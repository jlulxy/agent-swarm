"""
内存仓库实现

纯内存存储，用于测试和快速原型
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from copy import deepcopy

from storage.base import (
    BaseSessionRepository,
    BaseAgentRepository,
    BaseMessageRepository,
    BaseRelayRepository,
    BaseInterventionRepository,
    BaseUserRepository,
    SessionRecord,
    AgentRecord,
    MessageRecord,
    RelayStationRecord,
    RelayMessageRecord,
    InterventionRecord,
    UserRecord,
)


class MemoryRepository(
    BaseSessionRepository,
    BaseAgentRepository,
    BaseMessageRepository,
    BaseRelayRepository,
    BaseInterventionRepository,
    BaseUserRepository
):
    """内存仓库实现
    
    所有数据存储在字典中，服务重启后数据丢失
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}
        self._agents: Dict[str, AgentRecord] = {}  # key: f"{session_id}:{agent_id}"
        self._messages: Dict[str, MessageRecord] = {}  # key: message_id
        self._stations: Dict[str, RelayStationRecord] = {}  # key: f"{session_id}:{station_id}"
        self._relay_messages: Dict[str, RelayMessageRecord] = {}  # key: message_id
        self._interventions: Dict[str, InterventionRecord] = {}  # key: intervention_id
        self._users: Dict[str, UserRecord] = {}  # key: user_id
        self._users_by_username: Dict[str, str] = {}  # key: username -> user_id
    
    # ========== Session Repository ==========
    
    async def create_session(self, record: SessionRecord) -> SessionRecord:
        self._sessions[record.session_id] = deepcopy(record)
        return deepcopy(record)
    
    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        record = self._sessions.get(session_id)
        return deepcopy(record) if record else None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[SessionRecord]:
        if session_id not in self._sessions:
            return None
        
        record = self._sessions[session_id]
        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = datetime.now()
        
        return deepcopy(record)
    
    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            # 级联删除
            await self.delete_agents_by_session(session_id)
            await self.delete_messages_by_session(session_id)
            # 删除中继站和消息
            keys_to_delete = [k for k in self._stations if k.startswith(f"{session_id}:")]
            for key in keys_to_delete:
                del self._stations[key]
            keys_to_delete = [k for k, v in self._relay_messages.items() if v.session_id == session_id]
            for key in keys_to_delete:
                del self._relay_messages[key]
            # 删除干预记录
            keys_to_delete = [k for k, v in self._interventions.items() if v.session_id == session_id]
            for key in keys_to_delete:
                del self._interventions[key]
            return True
        return False
    
    async def list_sessions(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[SessionRecord]:
        records = list(self._sessions.values())
        
        if status:
            records = [r for r in records if r.status == status]
        
        if user_id:
            # 严格按用户隔离，只返回当前用户自己的会话
            records = [r for r in records if r.user_id == user_id]
        
        # 排序
        records.sort(
            key=lambda r: getattr(r, order_by, r.created_at),
            reverse=order_desc
        )
        
        # 分页
        return [deepcopy(r) for r in records[offset:offset + limit]]
    
    async def count_sessions(self, status: Optional[str] = None, user_id: Optional[str] = None) -> int:
        if status and user_id:
            return sum(1 for r in self._sessions.values() if r.status == status and r.user_id == user_id)
        elif status:
            return sum(1 for r in self._sessions.values() if r.status == status)
        elif user_id:
            return sum(1 for r in self._sessions.values() if r.user_id == user_id)
        return len(self._sessions)
    
    async def touch_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].last_active_at = datetime.now()
            return True
        return False
    
    async def cleanup_expired_sessions(self, timeout_minutes: int = 60) -> int:
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        count = 0
        
        for record in self._sessions.values():
            if record.status == "active" and record.last_active_at < cutoff_time:
                record.status = "expired"
                count += 1
        
        return count
    
    # ========== Agent Repository ==========
    
    async def create_agent(self, record: AgentRecord) -> AgentRecord:
        key = f"{record.session_id}:{record.agent_id}"
        self._agents[key] = deepcopy(record)
        return deepcopy(record)
    
    async def get_agent(self, agent_id: str, session_id: str) -> Optional[AgentRecord]:
        key = f"{session_id}:{agent_id}"
        record = self._agents.get(key)
        return deepcopy(record) if record else None
    
    async def update_agent(self, agent_id: str, session_id: str, updates: Dict[str, Any]) -> Optional[AgentRecord]:
        key = f"{session_id}:{agent_id}"
        if key not in self._agents:
            return None
        
        record = self._agents[key]
        for k, value in updates.items():
            if hasattr(record, k):
                setattr(record, k, value)
        record.updated_at = datetime.now()
        
        return deepcopy(record)
    
    async def list_agents_by_session(self, session_id: str) -> List[AgentRecord]:
        records = [
            deepcopy(r) for r in self._agents.values()
            if r.session_id == session_id
        ]
        records.sort(key=lambda r: r.created_at)
        return records
    
    async def delete_agents_by_session(self, session_id: str) -> int:
        keys_to_delete = [k for k in self._agents if k.startswith(f"{session_id}:")]
        for key in keys_to_delete:
            del self._agents[key]
        return len(keys_to_delete)
    
    # ========== Message Repository ==========
    
    async def create_message(self, record: MessageRecord) -> MessageRecord:
        self._messages[record.message_id] = deepcopy(record)
        return deepcopy(record)
    
    async def get_messages_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[MessageRecord]:
        records = [
            deepcopy(r) for r in self._messages.values()
            if r.session_id == session_id
        ]
        records.sort(key=lambda r: r.timestamp)
        return records[offset:offset + limit]
    
    async def delete_messages_by_session(self, session_id: str) -> int:
        keys_to_delete = [k for k, v in self._messages.items() if v.session_id == session_id]
        for key in keys_to_delete:
            del self._messages[key]
        return len(keys_to_delete)
    
    # ========== Relay Repository ==========
    
    async def create_station(self, record: RelayStationRecord) -> RelayStationRecord:
        key = f"{record.session_id}:{record.station_id}"
        self._stations[key] = deepcopy(record)
        return deepcopy(record)
    
    async def get_station(self, station_id: str, session_id: str) -> Optional[RelayStationRecord]:
        key = f"{session_id}:{station_id}"
        record = self._stations.get(key)
        return deepcopy(record) if record else None
    
    async def update_station(self, station_id: str, session_id: str, updates: Dict[str, Any]) -> Optional[RelayStationRecord]:
        key = f"{session_id}:{station_id}"
        if key not in self._stations:
            return None
        
        record = self._stations[key]
        for k, value in updates.items():
            if hasattr(record, k):
                setattr(record, k, value)
        
        return deepcopy(record)
    
    async def list_stations_by_session(self, session_id: str) -> List[RelayStationRecord]:
        records = [
            deepcopy(r) for r in self._stations.values()
            if r.session_id == session_id
        ]
        records.sort(key=lambda r: r.created_at)
        return records
    
    async def create_relay_message(self, record: RelayMessageRecord) -> RelayMessageRecord:
        self._relay_messages[record.message_id] = deepcopy(record)
        return deepcopy(record)
    
    async def get_relay_messages_by_station(
        self,
        station_id: str,
        session_id: str,
        limit: int = 100
    ) -> List[RelayMessageRecord]:
        records = [
            deepcopy(r) for r in self._relay_messages.values()
            if r.station_id == station_id and r.session_id == session_id
        ]
        records.sort(key=lambda r: r.timestamp)
        return records[:limit]
    
    async def get_relay_messages_by_session(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[RelayMessageRecord]:
        records = [
            deepcopy(r) for r in self._relay_messages.values()
            if r.session_id == session_id
        ]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
    
    # ========== Intervention Repository ==========
    
    async def create_intervention(self, record: InterventionRecord) -> InterventionRecord:
        self._interventions[record.intervention_id] = deepcopy(record)
        return deepcopy(record)
    
    async def get_interventions_by_session(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[InterventionRecord]:
        records = [
            deepcopy(r) for r in self._interventions.values()
            if r.session_id == session_id
        ]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
    
    # ========== User Repository ==========
    
    async def create_user(self, record: UserRecord) -> UserRecord:
        self._users[record.user_id] = deepcopy(record)
        self._users_by_username[record.username] = record.user_id
        return deepcopy(record)
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserRecord]:
        record = self._users.get(user_id)
        return deepcopy(record) if record else None
    
    async def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        user_id = self._users_by_username.get(username)
        if user_id:
            record = self._users.get(user_id)
            return deepcopy(record) if record else None
        return None
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[UserRecord]:
        if user_id not in self._users:
            return None
        
        record = self._users[user_id]
        for key, value in updates.items():
            if hasattr(record, key) and key not in ("user_id", "username", "password_hash"):
                setattr(record, key, value)
        record.updated_at = datetime.now()
        
        return deepcopy(record)
