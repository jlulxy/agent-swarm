"""Core Module - Agent Cluster 核心组件"""

from .models import (
    AgentStatus,
    RelayType,
    MessageRole,
    EmergentRole,
    SubagentConfig,
    SubagentState,
    RelayMessage,
    RelayStation,
    TaskPlan,
    TaskSession,
    Message,
    ToolDefinition,
    ToolCall,
    InterventionType,
    InterventionScope,
    HumanIntervention,
    InterventionDirective,
)

from .role_emergence import RoleEmergenceEngine, RoleEmergenceValidator
from .subagent import SubagentRuntime
from .relay_station import RelayStationCoordinator, AdaptiveRelayTrigger
from .master_agent import MasterAgent
from .direct_agent import DirectAgent
from .session_manager import SessionManager, get_session_manager, SessionInfo

__all__ = [
    # Models
    "AgentStatus",
    "RelayType",
    "MessageRole",
    "EmergentRole",
    "SubagentConfig",
    "SubagentState",
    "RelayMessage",
    "RelayStation",
    "TaskPlan",
    "TaskSession",
    "Message",
    "ToolDefinition",
    "ToolCall",
    "InterventionType",
    "InterventionScope",
    "HumanIntervention",
    "InterventionDirective",
    # Engines
    "RoleEmergenceEngine",
    "RoleEmergenceValidator",
    "SubagentRuntime",
    "RelayStationCoordinator",
    "AdaptiveRelayTrigger",
    "MasterAgent",
    "DirectAgent",
    # Session Management
    "SessionManager",
    "get_session_manager",
    "SessionInfo",
]
