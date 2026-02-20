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
from pathlib import Path

# 技能库路径
LIBRARY_PATH = Path(__file__).parent / "library"


def init_skills(library_path: str | Path | None = None) -> int:
    """
    初始化技能系统，加载所有技能
    
    Args:
        library_path: 技能库路径，默认使用内置库
        
    Returns:
        加载的技能数量
    """
    if library_path is None:
        library_path = LIBRARY_PATH
    
    registry = get_global_registry()
    return registry.register_all_from_directory(library_path)


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
    
    # 便捷函数
    "init_skills",
    "get_skill",
    "list_skills",
    "match_intent",
    
    # 常量
    "LIBRARY_PATH",
]
