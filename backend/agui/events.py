"""
AG-UI 协议事件定义

完整实现 AG-UI 协议的所有事件类型
参考: https://docs.ag-ui.com/concepts/events
"""

from enum import Enum
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class EventType(str, Enum):
    """AG-UI 事件类型"""
    
    # ========== Lifecycle Events ==========
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"
    
    # ========== Text Message Events ==========
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    
    # ========== Tool Call Events ==========
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"
    
    # ========== State Management Events ==========
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    
    # ========== Custom Events (扩展) ==========
    # Agent 状态事件
    AGENT_SPAWNED = "AGENT_SPAWNED"           # Subagent 创建
    AGENT_STATUS_CHANGED = "AGENT_STATUS_CHANGED"  # Agent 状态变化
    AGENT_PROGRESS = "AGENT_PROGRESS"          # Agent 进度更新
    AGENT_THINKING = "AGENT_THINKING"          # Agent 思考过程
    
    # 中继站事件
    RELAY_STATION_OPENED = "RELAY_STATION_OPENED"  # 中继站开启
    RELAY_MESSAGE_SENT = "RELAY_MESSAGE_SENT"      # 中继消息发送
    RELAY_STATION_CLOSED = "RELAY_STATION_CLOSED"  # 中继站关闭
    
    # 规划事件
    PLAN_GENERATED = "PLAN_GENERATED"          # 任务规划生成
    ROLE_EMERGED = "ROLE_EMERGED"              # 角色涌现
    
    # 人工干预事件
    INTERVENTION_REQUESTED = "INTERVENTION_REQUESTED"
    INTERVENTION_APPLIED = "INTERVENTION_APPLIED"
    INTERVENTION_BROADCAST = "INTERVENTION_BROADCAST"  # 人工干预广播到中继站
    
    # 会话事件 (新增 - 支持多客户端订阅)
    SESSION_CREATED = "SESSION_CREATED"               # 会话创建
    SESSION_STATE_CHANGED = "SESSION_STATE_CHANGED"   # 会话状态变更通知（用于列表刷新）


# ========== 基础事件模型 ==========

class BaseEvent(BaseModel):
    """基础事件"""
    type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        return f"event: {self.type.value}\ndata: {self.model_dump_json()}\n\n"


# ========== Lifecycle Events ==========

class RunStartedEvent(BaseEvent):
    """运行开始事件"""
    type: EventType = EventType.RUN_STARTED
    thread_id: str
    run_id: str


class RunFinishedEvent(BaseEvent):
    """运行结束事件"""
    type: EventType = EventType.RUN_FINISHED
    thread_id: str
    run_id: str


class RunErrorEvent(BaseEvent):
    """运行错误事件"""
    type: EventType = EventType.RUN_ERROR
    message: str
    code: Optional[str] = None


# ========== Text Message Events ==========

class TextMessageStartEvent(BaseEvent):
    """文本消息开始事件"""
    type: EventType = EventType.TEXT_MESSAGE_START
    message_id: str
    role: str = "assistant"


class TextMessageContentEvent(BaseEvent):
    """文本消息内容事件（流式）"""
    type: EventType = EventType.TEXT_MESSAGE_CONTENT
    message_id: str
    delta: str  # 增量内容


class TextMessageEndEvent(BaseEvent):
    """文本消息结束事件"""
    type: EventType = EventType.TEXT_MESSAGE_END
    message_id: str


# ========== Tool Call Events ==========

class ToolCallStartEvent(BaseEvent):
    """工具调用开始事件"""
    type: EventType = EventType.TOOL_CALL_START
    tool_call_id: str
    tool_call_name: str
    parent_message_id: Optional[str] = None


class ToolCallArgsEvent(BaseEvent):
    """工具调用参数事件（流式）"""
    type: EventType = EventType.TOOL_CALL_ARGS
    tool_call_id: str
    delta: str  # 增量参数 JSON


class ToolCallEndEvent(BaseEvent):
    """工具调用结束事件"""
    type: EventType = EventType.TOOL_CALL_END
    tool_call_id: str


class ToolCallResultEvent(BaseEvent):
    """工具调用结果事件"""
    type: EventType = EventType.TOOL_CALL_RESULT
    tool_call_id: str
    result: str


# ========== State Management Events ==========

class StateSnapshotEvent(BaseEvent):
    """状态快照事件"""
    type: EventType = EventType.STATE_SNAPSHOT
    snapshot: Dict[str, Any]


class StateDeltaEvent(BaseEvent):
    """状态增量事件"""
    type: EventType = EventType.STATE_DELTA
    delta: List[Dict[str, Any]]  # JSON Patch 格式


# ========== Custom Agent Events ==========

class AgentSpawnedEvent(BaseEvent):
    """Subagent 创建事件 - 增强版"""
    type: EventType = EventType.AGENT_SPAWNED
    agent_id: str
    agent_name: str
    role_name: str
    role_description: str
    capabilities: List[str]
    task_segment: str
    
    # 新增字段
    work_objective: Optional[str] = None          # 工作目标
    deliverables: List[str] = Field(default_factory=list)  # 预期交付物
    methodology: Optional[Dict[str, Any]] = None  # 工作方法论
    assigned_skills: List[Dict[str, str]] = Field(default_factory=list)  # 分配的技能
    expertise_level: str = "expert"               # 专业水平
    focus_areas: List[str] = Field(default_factory=list)  # 关注领域


class AgentStatusChangedEvent(BaseEvent):
    """Agent 状态变化事件"""
    type: EventType = EventType.AGENT_STATUS_CHANGED
    agent_id: str
    agent_name: str
    previous_status: str
    new_status: str
    reason: Optional[str] = None


class AgentProgressEvent(BaseEvent):
    """Agent 进度更新事件"""
    type: EventType = EventType.AGENT_PROGRESS
    agent_id: str
    agent_name: str
    progress: float  # 0-100
    current_step: str
    iterations: int


class AgentThinkingEvent(BaseEvent):
    """Agent 思考过程事件"""
    type: EventType = EventType.AGENT_THINKING
    agent_id: str
    agent_name: str
    thinking: str  # 思考内容（流式增量）


# ========== Relay Station Events ==========

class RelayStationOpenedEvent(BaseEvent):
    """中继站开启事件"""
    type: EventType = EventType.RELAY_STATION_OPENED
    station_id: str
    station_name: str
    phase: int
    participating_agents: List[Dict[str, str]]  # [{id, name}]


class RelayMessageSentEvent(BaseEvent):
    """中继消息发送事件"""
    type: EventType = EventType.RELAY_MESSAGE_SENT
    station_id: str
    message_id: str
    source_agent_id: str
    source_agent_name: str
    target_agent_ids: List[str]  # 空表示广播
    relay_type: str
    content: str
    importance: float
    metadata: Dict[str, Any] = Field(default_factory=dict)        # 消息元数据
    viewed_by: List[str] = Field(default_factory=list)            # 已查看的 Agent ID
    acknowledged_by: List[str] = Field(default_factory=list)      # 已确认的 Agent ID
    viewed_timestamps: Dict[str, str] = Field(default_factory=dict)  # Agent ID -> 查看时间


class RelayStationClosedEvent(BaseEvent):
    """中继站关闭事件"""
    type: EventType = EventType.RELAY_STATION_CLOSED
    station_id: str
    station_name: str
    summary: str  # 中继站汇总信息


# ========== Planning Events ==========

class PlanGeneratedEvent(BaseEvent):
    """任务规划生成事件"""
    type: EventType = EventType.PLAN_GENERATED
    plan_id: str
    original_task: str
    analysis: str
    phases: List[Dict[str, Any]]
    estimated_duration: int
    total_agents: int


class RoleEmergedEvent(BaseEvent):
    """角色涌现事件"""
    type: EventType = EventType.ROLE_EMERGED
    role_id: str
    role_name: str
    description: str
    capabilities: List[str]
    focus_areas: List[str]
    reasoning: str  # 为什么涌现这个角色


# ========== Human Intervention Events ==========

class InterventionRequestedEvent(BaseEvent):
    """请求人工干预事件"""
    type: EventType = EventType.INTERVENTION_REQUESTED
    request_id: str
    agent_id: Optional[str]
    reason: str
    options: List[Dict[str, Any]]  # 可选的干预操作


class InterventionAppliedEvent(BaseEvent):
    """人工干预已应用事件"""
    type: EventType = EventType.INTERVENTION_APPLIED
    intervention_id: str
    intervention_type: str
    target_agent_id: Optional[str]
    payload: Dict[str, Any]
    result: str


class InterventionBroadcastEvent(BaseEvent):
    """人工干预广播事件 - 通过中继站广播"""
    type: EventType = EventType.INTERVENTION_BROADCAST
    station_id: str                               # 中继站 ID
    intervention_id: str                          # 干预 ID
    intervention_type: str                        # 干预类型
    scope: str                                    # 作用范围
    source_name: str = "🧑‍💼 人类操作员"           # 来源名称
    target_agent_ids: List[str]                   # 目标 Agent（空表示广播）
    message_content: str                          # 中继消息内容
    priority: int                                 # 优先级
    importance: float                             # 重要性
    reason: str                                   # 干预原因
    payload: Dict[str, Any] = Field(default_factory=dict)  # 干预负载


# ========== Session Events (新增 - 多客户端订阅支持) ==========

class SessionCreatedEvent(BaseEvent):
    """会话创建事件"""
    type: EventType = EventType.SESSION_CREATED
    session_id: str


class SessionStateChangedEvent(BaseEvent):
    """会话状态变更事件 - 用于通知前端列表刷新
    
    当会话内发生重要变更时（如 Agent 涌现、状态变化、完成等），
    广播此事件给所有订阅者，前端可据此刷新会话列表。
    """
    type: EventType = EventType.SESSION_STATE_CHANGED
    session_id: str
    change_type: str  # "agent_added", "agent_status_changed", "completed", "error", etc.
    summary: Dict[str, Any] = Field(default_factory=dict)  # 变更摘要
    # 摘要示例:
    # - agent_added: {"agent_id": "xxx", "agent_name": "产品经理", "total_agents": 3}
    # - status_changed: {"status": "running", "progress": 50}
    # - completed: {"final_report": "...", "duration_seconds": 120}


# ========== 事件工厂 ==========

class EventFactory:
    """事件工厂 - 简化事件创建"""
    
    @staticmethod
    def run_started(thread_id: str, run_id: str) -> RunStartedEvent:
        return RunStartedEvent(thread_id=thread_id, run_id=run_id)
    
    @staticmethod
    def run_finished(thread_id: str, run_id: str) -> RunFinishedEvent:
        return RunFinishedEvent(thread_id=thread_id, run_id=run_id)
    
    @staticmethod
    def run_error(message: str, code: Optional[str] = None) -> RunErrorEvent:
        return RunErrorEvent(message=message, code=code)
    
    @staticmethod
    def text_message_start(message_id: str, role: str = "assistant") -> TextMessageStartEvent:
        return TextMessageStartEvent(message_id=message_id, role=role)
    
    @staticmethod
    def text_message_content(message_id: str, delta: str) -> TextMessageContentEvent:
        return TextMessageContentEvent(message_id=message_id, delta=delta)
    
    @staticmethod
    def text_message_end(message_id: str) -> TextMessageEndEvent:
        return TextMessageEndEvent(message_id=message_id)
    
    @staticmethod
    def agent_spawned(
        agent_id: str,
        agent_name: str,
        role_name: str,
        role_description: str,
        capabilities: List[str],
        task_segment: str
    ) -> AgentSpawnedEvent:
        return AgentSpawnedEvent(
            agent_id=agent_id,
            agent_name=agent_name,
            role_name=role_name,
            role_description=role_description,
            capabilities=capabilities,
            task_segment=task_segment
        )
    
    @staticmethod
    def agent_status_changed(
        agent_id: str,
        agent_name: str,
        previous_status: str,
        new_status: str,
        reason: Optional[str] = None
    ) -> AgentStatusChangedEvent:
        return AgentStatusChangedEvent(
            agent_id=agent_id,
            agent_name=agent_name,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason
        )
    
    @staticmethod
    def agent_progress(
        agent_id: str,
        agent_name: str,
        progress: float,
        current_step: str,
        iterations: int
    ) -> AgentProgressEvent:
        return AgentProgressEvent(
            agent_id=agent_id,
            agent_name=agent_name,
            progress=progress,
            current_step=current_step,
            iterations=iterations
        )
    
    @staticmethod
    def relay_station_opened(
        station_id: str,
        station_name: str,
        phase: int,
        participating_agents: List[Dict[str, str]]
    ) -> RelayStationOpenedEvent:
        return RelayStationOpenedEvent(
            station_id=station_id,
            station_name=station_name,
            phase=phase,
            participating_agents=participating_agents
        )
    
    @staticmethod
    def relay_message_sent(
        station_id: str,
        message_id: str,
        source_agent_id: str,
        source_agent_name: str,
        target_agent_ids: List[str],
        relay_type: str,
        content: str,
        importance: float
    ) -> RelayMessageSentEvent:
        return RelayMessageSentEvent(
            station_id=station_id,
            message_id=message_id,
            source_agent_id=source_agent_id,
            source_agent_name=source_agent_name,
            target_agent_ids=target_agent_ids,
            relay_type=relay_type,
            content=content,
            importance=importance
        )
    
    @staticmethod
    def intervention_broadcast(
        station_id: str,
        intervention_id: str,
        intervention_type: str,
        scope: str,
        target_agent_ids: List[str],
        message_content: str,
        priority: int,
        importance: float,
        reason: str,
        payload: Dict[str, Any] = None
    ) -> InterventionBroadcastEvent:
        return InterventionBroadcastEvent(
            station_id=station_id,
            intervention_id=intervention_id,
            intervention_type=intervention_type,
            scope=scope,
            target_agent_ids=target_agent_ids,
            message_content=message_content,
            priority=priority,
            importance=importance,
            reason=reason,
            payload=payload or {}
        )
    
    @staticmethod
    def intervention_applied(
        intervention_id: str,
        intervention_type: str,
        target_agent_id: Optional[str],
        payload: Dict[str, Any],
        result: str
    ) -> InterventionAppliedEvent:
        return InterventionAppliedEvent(
            intervention_id=intervention_id,
            intervention_type=intervention_type,
            target_agent_id=target_agent_id,
            payload=payload,
            result=result
        )
