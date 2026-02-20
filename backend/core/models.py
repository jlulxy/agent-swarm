"""
核心数据模型定义

定义 Agent 集群系统中的所有核心数据结构
"""

from enum import Enum
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============== 枚举类型 ==============

class AgentStatus(str, Enum):
    """Agent 状态"""
    PENDING = "pending"           # 等待启动
    PLANNING = "planning"         # 规划中
    RUNNING = "running"           # 执行中
    WAITING_RELAY = "waiting_relay"  # 等待中继
    RELAYING = "relaying"         # 中继同步中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    PAUSED = "paused"             # 已暂停（人工干预）
    CANCELLED = "cancelled"       # 已取消


class RelayType(str, Enum):
    """中继类型"""
    # === 发现类 ===
    DISCOVERY = "discovery"               # 关键发现通知（单向分享）
    INSIGHT = "insight"                   # 洞察/见解（深度分析）
    
    # === 对齐/协作类 ===
    ALIGNMENT_REQUEST = "alignment_request"   # 请求对齐（发起方）
    ALIGNMENT_RESPONSE = "alignment_response" # 响应对齐（响应方）
    ALIGNMENT = "alignment"               # 信息对齐（通用，向后兼容）
    
    # === 建议/反馈类 ===
    SUGGESTION = "suggestion"             # 建议（可选采纳）
    QUESTION = "question"                 # 疑问/求助
    CONFIRMATION = "confirmation"         # 确认/认可
    
    # === 状态类 ===
    CHECKPOINT = "checkpoint"             # 阶段性检查点
    CORRECTION = "correction"             # 纠偏调整
    COMPLETION = "completion"             # 完成通知
    
    # === 干预类 ===
    HUMAN_INTERVENTION = "human_intervention"  # 人工干预消息


class InterventionScope(str, Enum):
    """人工干预作用范围"""
    SINGLE = "single"             # 单个 Agent
    SELECTED = "selected"         # 选定的多个 Agent
    ALL = "all"                   # 所有 Agent
    BROADCAST = "broadcast"       # 广播（所有人可见但不强制执行）


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ============== 基础模型 ==============

class BaseModelWithTimestamp(BaseModel):
    """带时间戳的基础模型"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============== 技能相关模型 ==============

class SkillAssignment(BaseModel):
    """技能分配"""
    skill_name: str                     # 技能名称
    skill_display_name: str             # 显示名称
    reason: str = ""                    # 分配原因
    config: Dict[str, Any] = Field(default_factory=dict)  # 技能配置


# ============== Agent 相关模型 ==============

class WorkMethodology(BaseModel):
    """工作方法论"""
    approach: str                       # 总体方法/策略
    steps: List[str] = Field(default_factory=list)        # 具体步骤
    tools_and_frameworks: List[str] = Field(default_factory=list)  # 使用的工具和框架
    success_criteria: List[str] = Field(default_factory=list)      # 成功标准
    quality_metrics: List[str] = Field(default_factory=list)       # 质量指标


class EmergentRole(BaseModel):
    """涌现的角色定义 - 增强版"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                           # 角色名称，如"镜头分析师"
    description: str                    # 角色描述
    
    # 核心能力定义
    capabilities: List[str]             # 能力列表
    focus_areas: List[str]              # 关注领域
    expertise_level: str = "expert"     # 专业水平: novice, intermediate, expert, master
    
    # 工作目标与方法 (新增)
    work_objective: str = ""            # 工作目标：明确要达成什么
    deliverables: List[str] = Field(default_factory=list)  # 预期交付物
    methodology: Optional[WorkMethodology] = None  # 工作方法论
    
    # 技能配置 (新增)
    assigned_skills: List[SkillAssignment] = Field(default_factory=list)  # 分配的技能
    
    # Prompt 配置
    system_prompt: str                  # 系统提示词
    relay_triggers: List[str]           # 触发中继的条件描述
    
    # 元数据
    emergence_reasoning: str = ""       # 涌现这个角色的推理
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "镜头分析师",
                "description": "专注于分析电影镜头语言、构图和运镜技巧",
                "capabilities": ["镜头识别", "构图分析", "运镜解读"],
                "focus_areas": ["长镜头", "蒙太奇", "景深运用"],
                "work_objective": "深入分析电影的视觉叙事语言，揭示导演的艺术意图",
                "deliverables": ["镜头分析报告", "关键镜头解读", "视觉风格总结"],
                "methodology": {
                    "approach": "系统性镜头语言分析法",
                    "steps": ["观察整体视觉风格", "识别关键镜头", "分析技法运用", "总结导演意图"],
                    "tools_and_frameworks": ["镜头语言理论", "蒙太奇理论", "视觉符号学"],
                    "success_criteria": ["全面覆盖关键镜头", "准确识别技法", "深刻揭示艺术意图"]
                },
                "assigned_skills": [
                    {"skill_name": "reasoning", "skill_display_name": "推理分析", "reason": "用于深度分析镜头含义"}
                ],
                "system_prompt": "你是一位专业的电影镜头分析师...",
                "relay_triggers": ["发现关键镜头技法", "识别出导演风格特征"],
                "emergence_reasoning": "电影视觉分析需要专业的镜头语言解读能力"
            }
        }


class SubagentConfig(BaseModel):
    """Subagent 配置"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: EmergentRole                  # 涌现的角色
    task_segment: str                   # 分配的任务片段
    priority: int = 5                   # 优先级 1-10
    max_iterations: int = 10            # 最大迭代次数
    timeout_seconds: int = 300          # 超时时间
    
    # 中继配置
    relay_enabled: bool = True          # 是否启用中继
    relay_threshold: float = 0.7        # 中继触发阈值（置信度）


class SubagentState(BaseModelWithTimestamp):
    """Subagent 运行状态"""
    id: str
    config: SubagentConfig
    status: AgentStatus = AgentStatus.PENDING
    progress: float = 0.0               # 进度 0-100
    current_step: str = ""              # 当前步骤描述
    iterations: int = 0                 # 已执行迭代数
    
    # 输出
    thinking: str = ""                  # 思考过程
    partial_result: str = ""            # 部分结果
    final_result: Optional[str] = None
    
    # 工具调用
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 技能执行记录 (新增)
    skill_executions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 中继信息
    relay_messages_sent: List[Dict[str, Any]] = Field(default_factory=list)
    relay_messages_received: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 错误信息
    error: Optional[str] = None


# ============== 中继站模型 ==============

class RelayMessage(BaseModel):
    """中继消息"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: RelayType
    source_agent_id: str          # 发送者 Agent ID
    source_agent_name: str        # 发送者 Agent 名称
    target_agent_ids: List[str]   # 目标 Agent ID 列表（空表示广播）
    content: str                  # 消息内容
    importance: float = 0.5       # 重要性 0-1
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 消息查看记录
    viewed_by: List[str] = Field(default_factory=list)          # 已查看的 Agent ID 列表
    acknowledged_by: List[str] = Field(default_factory=list)    # 已确认的 Agent ID 列表
    viewed_timestamps: Dict[str, str] = Field(default_factory=dict)  # Agent ID -> 查看时间
    
    def mark_viewed(self, agent_id: str):
        """标记消息被 Agent 查看"""
        if agent_id not in self.viewed_by:
            self.viewed_by.append(agent_id)
            self.viewed_timestamps[agent_id] = datetime.now().isoformat()
    
    def mark_acknowledged(self, agent_id: str):
        """标记消息被 Agent 确认"""
        if agent_id not in self.acknowledged_by:
            self.acknowledged_by.append(agent_id)
            # 确认也意味着查看
            self.mark_viewed(agent_id)


class RelayStation(BaseModel):
    """中继站状态"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                     # 中继站名称，如"阶段1中继"
    phase: int                    # 所属阶段
    participating_agents: List[str]  # 参与的 Agent ID
    messages: List[RelayMessage] = Field(default_factory=list)
    is_active: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============== 任务模型 ==============

class TaskPlan(BaseModel):
    """任务规划"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_task: str            # 原始任务描述
    analysis: str                 # 任务分析
    emergent_roles: List[EmergentRole]  # 涌现的角色
    subagent_configs: List[SubagentConfig]  # Subagent 配置
    relay_stations: List[RelayStation]  # 中继站配置
    estimated_duration: int       # 预计耗时（秒）
    phases: List[Dict[str, Any]] = Field(default_factory=list)  # 执行阶段


class TaskSession(BaseModelWithTimestamp):
    """任务会话"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str                     # 用户输入的任务
    status: AgentStatus = AgentStatus.PENDING
    
    # 规划
    plan: Optional[TaskPlan] = None
    
    # 执行状态
    subagent_states: Dict[str, SubagentState] = Field(default_factory=dict)
    active_relay_station: Optional[str] = None
    current_phase: int = 0
    
    # 结果
    final_report: Optional[str] = None
    
    # 人工干预
    paused_agents: List[str] = Field(default_factory=list)
    user_interventions: List[Dict[str, Any]] = Field(default_factory=list)


# ============== 消息模型 ==============

class Message(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCall(BaseModel):
    """工具调用"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed


# ============== 人工干预模型 ==============

class InterventionType(str, Enum):
    """干预类型"""
    PAUSE = "pause"               # 暂停
    RESUME = "resume"             # 恢复
    RESTART = "restart"           # 重启
    ADJUST = "adjust"             # 调整参数
    INJECT = "inject"             # 注入信息
    CANCEL = "cancel"             # 取消


class HumanIntervention(BaseModel):
    """人工干预"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: InterventionType
    target_agent_id: Optional[str] = None  # None 表示针对整个任务
    target_agent_ids: List[str] = Field(default_factory=list)  # 多 Agent 目标
    payload: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    scope: InterventionScope = InterventionScope.SINGLE  # 作用范围
    priority: int = 5  # 优先级 1-10，10 最高
    broadcast_to_relay: bool = True  # 是否广播到中继站
    timestamp: datetime = Field(default_factory=datetime.now)


class InterventionDirective(BaseModel):
    """干预指令 - Agent 需要执行的具体操作"""
    action: str                           # 具体动作：adjust_focus, change_priority, add_constraint, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    urgency: str = "normal"               # 紧急程度：low, normal, high, critical
    acknowledgement_required: bool = True  # 是否需要 Agent 确认收到
