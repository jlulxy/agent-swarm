"""
存储层抽象基类

定义统一的数据访问接口，具体实现由各数据库后端提供
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


# ========== 数据记录类型 ==========

@dataclass
class UserRecord:
    """用户记录 - 数据库存储格式"""
    user_id: str
    username: str
    password_hash: str
    display_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata_json: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


@dataclass
class SessionRecord:
    """会话记录 - 数据库存储格式"""
    session_id: str
    task: str = ""
    status: str = "active"  # active, completed, expired, error
    provider: str = "openai"
    model: Optional[str] = None
    
    # 会话模式
    mode: str = "emergent"  # emergent(涌现模式) / direct(普通模式)
    
    # 用户归属
    user_id: Optional[str] = None
    
    # 任务计划（JSON 序列化）
    plan_json: Optional[str] = None
    
    # 最终报告
    final_report: Optional[str] = None
    
    # 错误信息
    error: Optional[str] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)
    
    # 元数据（JSON）
    metadata_json: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "user_id": self.user_id,
            "plan": json.loads(self.plan_json) if self.plan_json else None,
            "final_report": self.final_report,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRecord":
        """从字典创建"""
        return cls(
            session_id=data["session_id"],
            task=data.get("task", ""),
            status=data.get("status", "active"),
            provider=data.get("provider", "openai"),
            model=data.get("model"),
            mode=data.get("mode", "emergent"),
            user_id=data.get("user_id"),
            plan_json=json.dumps(data["plan"]) if data.get("plan") else None,
            final_report=data.get("final_report"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            last_active_at=datetime.fromisoformat(data["last_active_at"]) if data.get("last_active_at") else datetime.now(),
            metadata_json=json.dumps(data.get("metadata", {})),
        )


@dataclass
class AgentRecord:
    """Agent 记录"""
    agent_id: str
    session_id: str
    name: str
    role_name: str
    role_description: str = ""
    capabilities: str = "[]"  # JSON 数组
    task_segment: str = ""
    status: str = "pending"
    progress: int = 0
    current_step: str = ""
    iterations: int = 0
    thinking: str = ""
    partial_result: Optional[str] = None
    final_result: Optional[str] = None
    
    # 扩展字段
    work_objective: Optional[str] = None
    deliverables: str = "[]"  # JSON 数组
    methodology: Optional[str] = None
    assigned_skills: str = "[]"  # JSON 数组
    expertise_level: Optional[str] = None
    focus_areas: str = "[]"  # JSON 数组
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "name": self.name,
            "role_name": self.role_name,
            "role_description": self.role_description,
            "capabilities": json.loads(self.capabilities) if self.capabilities else [],
            "task_segment": self.task_segment,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "iterations": self.iterations,
            "thinking": self.thinking,
            "partial_result": self.partial_result,
            "final_result": self.final_result,
            "work_objective": self.work_objective,
            "deliverables": json.loads(self.deliverables) if self.deliverables else [],
            "methodology": self.methodology,
            "assigned_skills": json.loads(self.assigned_skills) if self.assigned_skills else [],
            "expertise_level": self.expertise_level,
            "focus_areas": json.loads(self.focus_areas) if self.focus_areas else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class MessageRecord:
    """消息记录"""
    message_id: str
    session_id: str
    role: str  # system, user, assistant, tool
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata_json: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


@dataclass
class RelayStationRecord:
    """中继站记录"""
    station_id: str
    session_id: str
    name: str
    phase: int = 0
    participating_agents: str = "[]"  # JSON 数组
    is_active: bool = True
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "session_id": self.session_id,
            "name": self.name,
            "phase": self.phase,
            "participating_agents": json.loads(self.participating_agents) if self.participating_agents else [],
            "is_active": self.is_active,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


@dataclass
class RelayMessageRecord:
    """中继消息记录"""
    message_id: str
    station_id: str
    session_id: str
    relay_type: str
    source_agent_id: str
    source_agent_name: str
    target_agent_ids: str = "[]"  # JSON 数组
    content: str = ""
    importance: int = 5
    viewed_by: str = "[]"  # JSON 数组
    acknowledged_by: str = "[]"  # JSON 数组
    viewed_timestamps: str = "{}"  # JSON 对象
    timestamp: datetime = field(default_factory=datetime.now)
    metadata_json: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "station_id": self.station_id,
            "session_id": self.session_id,
            "relay_type": self.relay_type,
            "source_agent_id": self.source_agent_id,
            "source_agent_name": self.source_agent_name,
            "target_agent_ids": json.loads(self.target_agent_ids) if self.target_agent_ids else [],
            "content": self.content,
            "importance": self.importance,
            "viewed_by": json.loads(self.viewed_by) if self.viewed_by else [],
            "acknowledged_by": json.loads(self.acknowledged_by) if self.acknowledged_by else [],
            "viewed_timestamps": json.loads(self.viewed_timestamps) if self.viewed_timestamps else {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
        }


@dataclass
class InterventionRecord:
    """人工干预记录"""
    intervention_id: str
    session_id: str
    intervention_type: str  # pause, resume, restart, adjust, inject, cancel
    scope: str = "single"  # single, selected, all, broadcast
    target_agent_id: Optional[str] = None
    target_agent_ids: str = "[]"  # JSON 数组
    payload_json: Optional[str] = None
    reason: str = ""
    priority: int = 5
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "session_id": self.session_id,
            "intervention_type": self.intervention_type,
            "scope": self.scope,
            "target_agent_id": self.target_agent_id,
            "target_agent_ids": json.loads(self.target_agent_ids) if self.target_agent_ids else [],
            "payload": json.loads(self.payload_json) if self.payload_json else None,
            "reason": self.reason,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ========== 抽象基类 ==========

class BaseSessionRepository(ABC):
    """会话仓库抽象基类"""
    
    @abstractmethod
    async def create_session(self, record: SessionRecord) -> SessionRecord:
        """创建会话"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """获取会话"""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[SessionRecord]:
        """更新会话"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    async def list_sessions(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[SessionRecord]:
        """列出会话"""
        pass
    
    @abstractmethod
    async def count_sessions(self, status: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """统计会话数量（按用户隔离）"""
        pass
    
    @abstractmethod
    async def touch_session(self, session_id: str) -> bool:
        """更新会话最后活跃时间"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, timeout_minutes: int = 60) -> int:
        """清理过期会话"""
        pass


class BaseAgentRepository(ABC):
    """Agent 仓库抽象基类"""
    
    @abstractmethod
    async def create_agent(self, record: AgentRecord) -> AgentRecord:
        """创建 Agent 记录"""
        pass
    
    @abstractmethod
    async def get_agent(self, agent_id: str, session_id: str) -> Optional[AgentRecord]:
        """获取 Agent"""
        pass
    
    @abstractmethod
    async def update_agent(self, agent_id: str, session_id: str, updates: Dict[str, Any]) -> Optional[AgentRecord]:
        """更新 Agent"""
        pass
    
    @abstractmethod
    async def list_agents_by_session(self, session_id: str) -> List[AgentRecord]:
        """获取会话的所有 Agent"""
        pass
    
    @abstractmethod
    async def delete_agents_by_session(self, session_id: str) -> int:
        """删除会话的所有 Agent"""
        pass


class BaseMessageRepository(ABC):
    """消息仓库抽象基类"""
    
    @abstractmethod
    async def create_message(self, record: MessageRecord) -> MessageRecord:
        """创建消息"""
        pass
    
    @abstractmethod
    async def get_messages_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[MessageRecord]:
        """获取会话的消息"""
        pass
    
    @abstractmethod
    async def delete_messages_by_session(self, session_id: str) -> int:
        """删除会话的所有消息"""
        pass


class BaseRelayRepository(ABC):
    """中继站仓库抽象基类"""
    
    @abstractmethod
    async def create_station(self, record: RelayStationRecord) -> RelayStationRecord:
        """创建中继站"""
        pass
    
    @abstractmethod
    async def get_station(self, station_id: str, session_id: str) -> Optional[RelayStationRecord]:
        """获取中继站"""
        pass
    
    @abstractmethod
    async def update_station(self, station_id: str, session_id: str, updates: Dict[str, Any]) -> Optional[RelayStationRecord]:
        """更新中继站"""
        pass
    
    @abstractmethod
    async def list_stations_by_session(self, session_id: str) -> List[RelayStationRecord]:
        """获取会话的所有中继站"""
        pass
    
    @abstractmethod
    async def create_relay_message(self, record: RelayMessageRecord) -> RelayMessageRecord:
        """创建中继消息"""
        pass
    
    @abstractmethod
    async def get_relay_messages_by_station(
        self,
        station_id: str,
        session_id: str,
        limit: int = 100
    ) -> List[RelayMessageRecord]:
        """获取中继站的消息"""
        pass
    
    @abstractmethod
    async def get_relay_messages_by_session(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[RelayMessageRecord]:
        """获取会话的所有中继消息"""
        pass


class BaseInterventionRepository(ABC):
    """干预记录仓库抽象基类"""
    
    @abstractmethod
    async def create_intervention(self, record: InterventionRecord) -> InterventionRecord:
        """创建干预记录"""
        pass
    
    @abstractmethod
    async def get_interventions_by_session(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[InterventionRecord]:
        """获取会话的干预记录"""
        pass


class BaseUserRepository(ABC):
    """用户仓库抽象基类"""
    
    @abstractmethod
    async def create_user(self, record: UserRecord) -> UserRecord:
        """创建用户"""
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        """通过 user_id 获取用户"""
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        """通过 username 获取用户"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[UserRecord]:
        """更新用户信息"""
        pass
