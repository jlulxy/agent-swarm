import os
import platform
import shutil
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .registry import SkillRegistry, get_global_registry

logger = logging.getLogger(__name__)


@dataclass
class SkillsRuntimeConfig:
    max_tools_per_run: int = 12
    max_tool_rounds: int = 4
    tool_detect_timeout_sec: int = 60
    skill_exec_timeout_sec: int = 45
    max_total_tool_time_sec: int = 180
    snapshot_ttl_sec: int = 300
    strict_gating: bool = False

    @classmethod
    def from_env(cls) -> "SkillsRuntimeConfig":
        def _int(key: str, default: int) -> int:
            raw = os.getenv(key)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        def _bool(key: str, default: bool) -> bool:
            raw = os.getenv(key)
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            max_tools_per_run=max(1, _int("SKILLS_MAX_TOOLS_PER_RUN", 12)),
            max_tool_rounds=max(1, _int("SKILLS_MAX_TOOL_ROUNDS", 4)),
            tool_detect_timeout_sec=max(10, _int("SKILLS_TOOL_DETECT_TIMEOUT_SEC", 60)),
            skill_exec_timeout_sec=max(5, _int("SKILLS_SKILL_EXEC_TIMEOUT_SEC", 45)),
            max_total_tool_time_sec=max(15, _int("SKILLS_MAX_TOTAL_TOOL_TIME_SEC", 180)),
            snapshot_ttl_sec=max(10, _int("SKILLS_SNAPSHOT_TTL_SEC", 300)),
            strict_gating=_bool("SKILLS_STRICT_GATING", False),
        )


@dataclass
class SkillSnapshot:
    skill_names: List[str]
    created_at: float
    registry_updated_at: float


class SkillsRuntimeManager:
    def __init__(self, registry: Optional[SkillRegistry] = None, config: Optional[SkillsRuntimeConfig] = None):
        self.registry = registry or get_global_registry()
        self.config = config or SkillsRuntimeConfig.from_env()
        self._session_snapshots: Dict[str, SkillSnapshot] = {}

    def get_budget(self) -> SkillsRuntimeConfig:
        return self.config

    def clear_session_snapshot(self, session_id: str):
        self._session_snapshots.pop(session_id, None)

    def resolve_skills_for_session(self, session_id: str, task: str = "", force_refresh: bool = False) -> List[str]:
        now = time.time()
        registry_ts = self.registry.get_last_update_timestamp()
        snapshot = self._session_snapshots.get(session_id)

        if (
            not force_refresh
            and snapshot
            and (now - snapshot.created_at) <= self.config.snapshot_ttl_sec
            and snapshot.registry_updated_at >= registry_ts
        ):
            return snapshot.skill_names

        selected = self._resolve_runtime_skill_names(task=task)
        self._session_snapshots[session_id] = SkillSnapshot(
            skill_names=selected,
            created_at=now,
            registry_updated_at=registry_ts,
        )
        return selected

    def _resolve_runtime_skill_names(self, task: str = "") -> List[str]:
        skills = list(self.registry.get_all().values())
        scored = []

        task_lower = (task or "").lower()
        for skill in skills:
            ok, reason = self._is_skill_eligible(skill)
            if not ok:
                logger.info("[SkillsRuntime] Skip skill '%s': %s", skill.name, reason)
                continue

            score = int(skill.metadata.priority)

            if task_lower and skill.metadata.trigger_keywords:
                for kw in skill.metadata.trigger_keywords:
                    if kw and kw.lower() in task_lower:
                        score -= 20
                        break

            scored.append((score, skill.name))

        scored.sort(key=lambda x: (x[0], x[1]))
        selected = [name for _, name in scored[: self.config.max_tools_per_run]]
        return selected

    def _is_skill_eligible(self, skill) -> tuple[bool, str]:
        meta = skill.metadata

        # OS gating（默认强约束）
        if meta.requires_os:
            runtime_os = platform.system().lower()
            normalized = {os_name.strip().lower() for os_name in meta.requires_os if os_name.strip()}
            if runtime_os not in normalized:
                return False, f"requires_os={sorted(normalized)}, runtime_os={runtime_os}"

        if not self.config.strict_gating:
            return True, "soft-gating"

        # bin gating（严格模式）
        if meta.requires_bins:
            missing_bins = [b for b in meta.requires_bins if b and shutil.which(b) is None]
            if missing_bins:
                return False, f"missing_bins={missing_bins}"

        # env gating（严格模式）
        if meta.requires_envs:
            missing_envs = [k for k in meta.requires_envs if k and not os.getenv(k)]
            if missing_envs:
                return False, f"missing_envs={missing_envs}"

        return True, "ok"


_runtime_manager: Optional[SkillsRuntimeManager] = None


def get_runtime_manager(registry: Optional[SkillRegistry] = None) -> SkillsRuntimeManager:
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = SkillsRuntimeManager(registry=registry)
    elif registry is not None:
        _runtime_manager.registry = registry
    return _runtime_manager
