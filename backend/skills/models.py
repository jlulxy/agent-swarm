"""
Skills - 数据模型

参照 Anthropic Agent Skills 标准设计
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid


class SkillTriggerType(str, Enum):
    """技能触发类型"""
    ALWAYS = "always"           # 总是激活
    ON_DEMAND = "on_demand"     # 按需激活（显式调用）
    AUTO_DETECT = "auto_detect" # 自动检测（基于用户意图）


class SkillResourceType(str, Enum):
    """资源类型"""
    REFERENCE = "reference"     # 参考文档
    SCRIPT = "script"           # 可执行脚本
    TEMPLATE = "template"       # 模板文件
    EXAMPLE = "example"         # 示例文件
    ASSET = "asset"             # 静态资源


class SkillMetadata(BaseModel):
    """
    技能元数据 - 对应 SKILL.md 的 YAML Front Matter
    
    必需字段：
    - name: 技能唯一标识（小写，空格用连字符，最大64字符）
    - description: 功能描述和使用场景（最大1024字符）
    
    可选字段：
    - version: 版本号
    - author: 作者
    - tags: 标签列表
    - dependencies: 依赖的其他技能或包
    - triggers: 触发条件关键词
    """
    name: str = Field(..., max_length=64, pattern=r'^[a-z0-9-]+$')
    description: str = Field(..., max_length=1024)
    
    # 可选元数据
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = Field(default_factory=list)
    priority: int = 100  # 数值越小优先级越高
    
    # 依赖关系
    dependencies: List[str] = Field(default_factory=list)  # 依赖的包或其他技能
    requires_packages: List[str] = Field(default_factory=list)  # Python 包依赖
    
    # 运行时可用性约束（gating）
    requires_os: List[str] = Field(default_factory=list)  # 如: ["darwin", "linux"]
    requires_bins: List[str] = Field(default_factory=list)  # 如: ["python3", "ffmpeg"]
    requires_envs: List[str] = Field(default_factory=list)  # 如: ["SERPAPI_API_KEY"]
    
    # 触发配置
    trigger_type: SkillTriggerType = SkillTriggerType.AUTO_DETECT
    trigger_keywords: List[str] = Field(default_factory=list)  # 触发关键词
    
    # 显示配置
    display_name: Optional[str] = None  # 显示名称（默认使用 name）
    icon: Optional[str] = None  # 图标
    category: Optional[str] = None  # 分类
    
    @property
    def display(self) -> str:
        """获取显示名称"""
        return self.display_name or self.name.replace('-', ' ').title()


class SkillInstruction(BaseModel):
    """
    技能指令 - 对应 SKILL.md 的 Markdown 内容
    
    包含：
    - raw_content: 原始 Markdown 内容
    - sections: 解析后的章节
    - workflow: 工作流程步骤
    - guidelines: 指导原则
    - examples: 示例
    """
    raw_content: str = ""  # 原始 Markdown 内容
    
    # 解析后的结构化内容
    title: str = ""  # 标题
    overview: str = ""  # 概述
    
    # 工作流程（SOP）
    workflow: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 指导原则
    guidelines: List[str] = Field(default_factory=list)
    
    # 示例
    examples: List[Dict[str, str]] = Field(default_factory=list)
    
    # 章节内容
    sections: Dict[str, str] = Field(default_factory=dict)
    
    # 安全检查
    safety_checks: List[str] = Field(default_factory=list)
    
    # 成功标准
    success_criteria: List[str] = Field(default_factory=list)


class SkillResource(BaseModel):
    """
    技能资源文件
    
    支持的资源类型：
    - reference: 参考文档（如 REFERENCE.md, GUIDE.md）
    - script: 可执行脚本（如 scripts/helper.py）
    - template: 模板文件（如 templates/report.md）
    - example: 示例文件
    - asset: 静态资源
    """
    name: str  # 资源名称
    path: str  # 相对路径
    resource_type: SkillResourceType
    
    # 内容（懒加载）
    content: Optional[str] = None
    
    # 元信息
    description: Optional[str] = None
    file_size: Optional[int] = None
    last_modified: Optional[datetime] = None
    
    def load_content(self, base_path: Path) -> str:
        """加载资源内容"""
        full_path = base_path / self.path
        if full_path.exists():
            self.content = full_path.read_text(encoding='utf-8')
            self.file_size = full_path.stat().st_size
            self.last_modified = datetime.fromtimestamp(full_path.stat().st_mtime)
        return self.content or ""


class Skill(BaseModel):
    """
    技能 - 完整的技能定义
    
    一个技能包含：
    1. metadata: 元数据（来自 SKILL.md 的 YAML Front Matter）
    2. instruction: 指令（来自 SKILL.md 的 Markdown 内容）
    3. resources: 资源文件（参考文档、脚本、模板等）
    
    目录结构示例：
    ```
    my-skill/
    ├── SKILL.md              # 必需：主文件
    ├── REFERENCE.md          # 可选：参考文档
    ├── EXAMPLES.md           # 可选：示例
    ├── scripts/              # 可选：脚本目录
    │   └── helper.py
    └── templates/            # 可选：模板目录
        └── output.md
    ```
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # 核心内容
    metadata: SkillMetadata
    instruction: SkillInstruction
    
    # 资源文件
    resources: List[SkillResource] = Field(default_factory=list)
    
    # 文件系统信息
    skill_path: Optional[str] = None  # 技能目录路径
    
    # 运行时状态
    is_loaded: bool = False
    load_time: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def display_name(self) -> str:
        return self.metadata.display
    
    @property
    def description(self) -> str:
        return self.metadata.description
    
    def get_resource(self, name: str) -> Optional[SkillResource]:
        """获取指定资源"""
        for resource in self.resources:
            if resource.name == name:
                return resource
        return None
    
    def get_resources_by_type(self, resource_type: SkillResourceType) -> List[SkillResource]:
        """按类型获取资源"""
        return [r for r in self.resources if r.resource_type == resource_type]
    
    def get_scripts(self) -> List[SkillResource]:
        """获取所有脚本"""
        return self.get_resources_by_type(SkillResourceType.SCRIPT)
    
    def get_references(self) -> List[SkillResource]:
        """获取所有参考文档"""
        return self.get_resources_by_type(SkillResourceType.REFERENCE)
    
    def to_system_prompt(self, include_resources: bool = False) -> str:
        """
        生成系统提示内容
        
        渐进式披露：
        - 默认只包含核心指令
        - 按需包含参考资源
        """
        parts = []
        
        # 标题和描述
        parts.append(f"# {self.display_name}")
        parts.append(f"\n{self.description}\n")
        
        # 核心指令
        if self.instruction.raw_content:
            parts.append(self.instruction.raw_content)
        
        # 可选：包含参考资源
        if include_resources:
            references = self.get_references()
            for ref in references:
                if ref.content:
                    parts.append(f"\n## {ref.name}\n")
                    parts.append(ref.content)
        
        return "\n".join(parts)
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Tool 格式
        
        用于 Function Calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "要执行的具体任务"
                        },
                        "context": {
                            "type": "string",
                            "description": "任务上下文信息"
                        },
                        "options": {
                            "type": "object",
                            "description": "额外选项"
                        }
                    },
                    "required": ["task"]
                }
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.metadata.version,
            "author": self.metadata.author,
            "tags": self.metadata.tags,
            "priority": self.metadata.priority,
            "category": self.metadata.category,
            "requires_os": self.metadata.requires_os,
            "requires_bins": self.metadata.requires_bins,
            "requires_envs": self.metadata.requires_envs,
            "trigger_type": self.metadata.trigger_type.value,
            "trigger_keywords": self.metadata.trigger_keywords,
            "resources": [
                {
                    "name": r.name,
                    "type": r.resource_type.value,
                    "path": r.path
                }
                for r in self.resources
            ],
            "workflow": self.instruction.workflow,
            "is_loaded": self.is_loaded
        }


class SkillExecutionContext(BaseModel):
    """技能执行上下文"""
    skill_name: str
    agent_id: str
    agent_name: str
    task: str
    
    # 对话历史
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # 共享上下文（跨技能）
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    
    # 已加载的资源内容
    loaded_resources: Dict[str, str] = Field(default_factory=dict)
    
    # 执行选项
    options: Dict[str, Any] = Field(default_factory=dict)


class SkillExecutionResult(BaseModel):
    """技能执行结果"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    success: bool
    
    # 结果内容
    result: Any = None
    result_type: str = "text"  # text, json, markdown, html
    summary: str = ""
    
    # 执行信息
    execution_time_ms: float = 0
    tokens_used: int = 0
    
    # 错误信息
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 产出的资源（如生成的文件）
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    
    def to_message(self) -> str:
        """转换为可注入对话的消息"""
        if self.success:
            return f"[技能 {self.skill_name} 执行完成]\n{self.summary or self.result}"
        else:
            return f"[技能 {self.skill_name} 执行失败]\n错误: {self.error}"
