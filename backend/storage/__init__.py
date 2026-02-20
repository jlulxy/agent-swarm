"""
数据存储层 (Storage Layer)

采用 Repository Pattern + 依赖注入的设计，支持多种数据库后端：
- SQLite (默认，适合开发和单机部署)
- MySQL (生产环境)
- PostgreSQL (生产环境)

架构设计：
1. BaseRepository - 抽象基类，定义统一接口
2. SQLiteRepository / MySQLRepository / PostgreSQLRepository - 具体实现
3. RepositoryFactory - 工厂模式，根据配置创建实例
4. 依赖注入 - SessionManager 通过注入获取 Repository
"""

from storage.base import (
    BaseSessionRepository,
    BaseMessageRepository,
    BaseUserRepository,
    SessionRecord,
    MessageRecord,
    AgentRecord,
    RelayStationRecord,
    InterventionRecord,
    UserRecord,
)
from storage.factory import RepositoryFactory, get_repository
from storage.config import StorageConfig, StorageType

__all__ = [
    # 基类和数据记录
    "BaseSessionRepository",
    "BaseMessageRepository",
    "BaseUserRepository",
    "SessionRecord",
    "MessageRecord",
    "AgentRecord",
    "RelayStationRecord",
    "InterventionRecord",
    "UserRecord",
    # 工厂和配置
    "RepositoryFactory",
    "get_repository",
    "StorageConfig",
    "StorageType",
]
