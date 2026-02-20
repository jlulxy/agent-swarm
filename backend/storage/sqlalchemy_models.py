"""
SQLAlchemy ORM 模型定义

这些模型用于 SQLite、MySQL、PostgreSQL 等关系型数据库
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, DateTime,
    ForeignKey, Index, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class UserModel(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(64), default="")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    metadata_json = Column(Text, nullable=True)
    
    # 关系
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    """会话表"""
    __tablename__ = "sessions"
    
    session_id = Column(String(64), primary_key=True)
    task = Column(Text, default="")
    status = Column(String(32), default="active", index=True)
    provider = Column(String(32), default="openai")
    model = Column(String(64), nullable=True)
    
    # 会话模式：emergent(涌现模式) / direct(普通模式)
    mode = Column(String(32), default="emergent", index=True)
    
    # 用户归属（nullable 兼容旧数据）
    user_id = Column(String(64), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 任务计划（JSON）
    plan_json = Column(Text, nullable=True)
    
    # 结果
    final_report = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_active_at = Column(DateTime, default=datetime.now, index=True)
    
    # 元数据
    metadata_json = Column(Text, nullable=True)
    
    # 关系
    user = relationship("UserModel", back_populates="sessions")
    agents = relationship("AgentModel", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    relay_stations = relationship("RelayStationModel", back_populates="session", cascade="all, delete-orphan")
    interventions = relationship("InterventionModel", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_status_created", "status", "created_at"),
    )


class AgentModel(Base):
    """Agent 表"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(128), nullable=False)
    role_name = Column(String(128), nullable=False)
    role_description = Column(Text, default="")
    capabilities = Column(Text, default="[]")  # JSON
    task_segment = Column(Text, default="")
    
    status = Column(String(32), default="pending")
    progress = Column(Integer, default=0)
    current_step = Column(Text, default="")
    iterations = Column(Integer, default=0)
    thinking = Column(Text, default="")
    partial_result = Column(Text, nullable=True)
    final_result = Column(Text, nullable=True)
    
    # 扩展字段
    work_objective = Column(Text, nullable=True)
    deliverables = Column(Text, default="[]")  # JSON
    methodology = Column(Text, nullable=True)
    assigned_skills = Column(Text, default="[]")  # JSON
    expertise_level = Column(String(32), nullable=True)
    focus_areas = Column(Text, default="[]")  # JSON
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    session = relationship("SessionModel", back_populates="agents")
    
    __table_args__ = (
        Index("idx_agents_session_agent", "session_id", "agent_id", unique=True),
    )


class MessageModel(Base):
    """消息表"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(32), nullable=False)  # system, user, assistant, tool
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    metadata_json = Column(Text, nullable=True)
    
    # 关系
    session = relationship("SessionModel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_session_time", "session_id", "timestamp"),
    )


class RelayStationModel(Base):
    """中继站表"""
    __tablename__ = "relay_stations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(128), nullable=False)
    phase = Column(Integer, default=0)
    participating_agents = Column(Text, default="[]")  # JSON
    is_active = Column(Boolean, default=True)
    summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    closed_at = Column(DateTime, nullable=True)
    
    # 关系
    session = relationship("SessionModel", back_populates="relay_stations")
    # 注意：relay_messages 关系已移除，因为复合外键关系过于复杂
    # 改用通过 session_id + station_id 查询的方式
    
    __table_args__ = (
        Index("idx_relay_stations_session", "session_id", "station_id", unique=True),
    )


class RelayMessageModel(Base):
    """中继消息表"""
    __tablename__ = "relay_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(64), nullable=False, index=True)
    station_id = Column(String(64), nullable=True)  # 可为空，因为不是所有消息都有 station
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    relay_type = Column(String(32), nullable=False)
    source_agent_id = Column(String(64), nullable=False)
    source_agent_name = Column(String(128), nullable=False)
    target_agent_ids = Column(Text, default="[]")  # JSON
    content = Column(Text, default="")
    importance = Column(Integer, default=5)
    
    viewed_by = Column(Text, default="[]")  # JSON
    acknowledged_by = Column(Text, default="[]")  # JSON
    viewed_timestamps = Column(Text, default="{}")  # JSON
    
    timestamp = Column(DateTime, default=datetime.now, index=True)
    metadata_json = Column(Text, nullable=True)
    
    # 注意：移除复杂的复合外键关系，改用简单的 session_id 外键
    # station 关系可以通过 station_id + session_id 手动查询
    
    __table_args__ = (
        Index("idx_relay_messages_session", "session_id", "timestamp"),
        Index("idx_relay_messages_station", "station_id", "session_id", "timestamp"),
    )


class InterventionModel(Base):
    """干预记录表"""
    __tablename__ = "interventions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    intervention_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    intervention_type = Column(String(32), nullable=False)  # pause, resume, etc.
    scope = Column(String(32), default="single")
    target_agent_id = Column(String(64), nullable=True)
    target_agent_ids = Column(Text, default="[]")  # JSON
    payload_json = Column(Text, nullable=True)
    reason = Column(Text, default="")
    priority = Column(Integer, default=5)
    
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # 关系
    session = relationship("SessionModel", back_populates="interventions")
    
    __table_args__ = (
        Index("idx_interventions_session", "session_id", "timestamp"),
    )


def create_database_engine(connection_url: str, echo: bool = False, pool_size: int = 5):
    """创建数据库引擎
    
    Args:
        connection_url: 数据库连接 URL
        echo: 是否打印 SQL
        pool_size: 连接池大小
    """
    # SQLite 特殊处理
    if connection_url.startswith("sqlite"):
        # SQLite 需要特殊配置
        engine = create_engine(
            connection_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            connection_url,
            echo=echo,
            pool_size=pool_size,
            pool_pre_ping=True,
        )
    
    return engine


def create_tables(engine):
    """创建所有表"""
    Base.metadata.create_all(engine)
    # 自动迁移：为已有表添加缺失的列
    _auto_migrate(engine)


def _auto_migrate(engine):
    """自动迁移：检查并添加缺失的列（兼容 SQLite）"""
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    
    # 定义需要迁移的列: (表名, 列名, SQL 类型, 默认值)
    migrations = [
        ("sessions", "mode", "VARCHAR(32)", "'emergent'"),
    ]
    
    with engine.connect() as conn:
        for table_name, column_name, col_type, default_val in migrations:
            if table_name not in inspector.get_table_names():
                continue
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
            if column_name not in existing_columns:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type} DEFAULT {default_val}"
                conn.execute(text(sql))
                conn.commit()
                print(f"[Migration] Added column '{column_name}' to table '{table_name}'")


def get_session_factory(engine):
    """获取会话工厂"""
    return sessionmaker(bind=engine, expire_on_commit=False)
