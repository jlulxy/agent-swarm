"""
Skills 系统 - 基于 SKILL.md 标准的技能框架

设计原则：
1. SKILL.md 标准格式 - 每个技能由 Markdown 文件定义
2. 渐进式披露 - 按需加载资源内容
3. SOP 化工作流 - 结构化的标准作业程序
4. 动态加载 - 支持热更新和运行时重载

核心组件：
- Skill: 技能数据模型
- SkillRegistry: 技能注册表（统一管理）
- SkillExecutor: 技能执行器
- AgentSkillSet: Agent 技能集
"""

import os
from pathlib import Path
from typing import List

from .models import (
    Skill,
    SkillMetadata,
    SkillInstruction,
    SkillResource,
    SkillResourceType,
    SkillTriggerType,
    SkillExecutionContext,
    SkillExecutionResult,
)
from .registry import (
    SkillRegistry,
    get_global_registry,
)
from .executor import (
    SkillExecutor,
    AgentSkillSet,
)
from .loader import SkillLoader
from .runtime import SkillsRuntimeManager, get_runtime_manager

# 技能库路径
LIBRARY_PATH = Path(__file__).parent / "library"


def _parse_bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_skill_source_dirs(library_path: str | Path | None = None) -> List[Path]:
    """解析技能加载目录（按优先级从低到高）。"""
    builtin_path = Path(library_path) if library_path is not None else LIBRARY_PATH
    project_root = Path(__file__).resolve().parents[2]

    # 约定：workspace 级 skills 放在项目根目录 `skills/`
    workspace_default = project_root / "skills"
    workspace_path = Path(os.getenv("SKILLS_WORKSPACE_DIR", str(workspace_default)))
    enable_workspace = _parse_bool_env("SKILLS_ENABLE_WORKSPACE", True)

    # 额外目录：支持逗号分隔或 os.pathsep 分隔
    extra_dirs_raw = os.getenv("SKILLS_EXTRA_DIRS", "").strip()
    extra_dirs: List[Path] = []
    if extra_dirs_raw:
        normalized = extra_dirs_raw.replace(",", os.pathsep)
        for item in normalized.split(os.pathsep):
            item = item.strip()
            if item:
                extra_dirs.append(Path(item))

    dirs: List[Path] = []
    dirs.extend(extra_dirs)
    dirs.append(builtin_path)
    if enable_workspace:
        dirs.append(workspace_path)

    return dirs


def init_skills(library_path: str | Path | None = None) -> int:
    """
    初始化技能系统，加载所有技能

    加载顺序（后加载覆盖前加载）：
    1. extra dirs（可选）
    2. builtin library
    3. workspace skills（可选）

    Args:
        library_path: 内置技能库路径，默认使用 `backend/skills/library`

    Returns:
        最终注册的技能数量
    """
    registry = get_global_registry()
    registry.clear()

    source_dirs = _resolve_skill_source_dirs(library_path)
    for source_dir in source_dirs:
        if source_dir.exists() and source_dir.is_dir():
            loaded = registry.register_all_from_directory(source_dir)
            print(f"[Skills] Loaded {loaded} skills from: {source_dir}")
        else:
            print(f"[Skills] Skip missing dir: {source_dir}")

    final_count = registry.count()
    print(f"[Skills] Final active skills: {final_count}")

    # 预热运行时管理器（配置从环境变量读取）
    get_runtime_manager(registry)

    return final_count


def get_skill(name: str) -> Skill | None:
    """获取技能"""
    return get_global_registry().get(name)


def list_skills() -> list[str]:
    """列出所有技能名称"""
    return get_global_registry().list_names()


def match_intent(user_input: str, top_k: int = 3) -> list[tuple[str, float]]:
    """
    意图匹配

    Args:
        user_input: 用户输入
        top_k: 返回前 k 个匹配

    Returns:
        [(skill_name, score), ...]
    """
    matches = get_global_registry().match_intent(user_input, top_k)
    return [(skill.name, score) for skill, score in matches]


__all__ = [
    # 核心模型
    "Skill",
    "SkillMetadata",
    "SkillInstruction",
    "SkillResource",
    "SkillResourceType",
    "SkillTriggerType",
    "SkillExecutionContext",
    "SkillExecutionResult",

    # 注册和执行
    "SkillRegistry",
    "get_global_registry",
    "SkillExecutor",
    "AgentSkillSet",
    "SkillLoader",
    "SkillsRuntimeManager",
    "get_runtime_manager",

    # 便捷函数
    "init_skills",
    "get_skill",
    "list_skills",
    "match_intent",

    # 常量
    "LIBRARY_PATH",
]
