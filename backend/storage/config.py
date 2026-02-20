"""
存储配置

支持通过环境变量或配置文件设置数据库连接
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class StorageType(Enum):
    """存储类型枚举"""
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MEMORY = "memory"  # 纯内存，用于测试


@dataclass
class StorageConfig:
    """存储配置"""
    
    # 存储类型
    storage_type: StorageType = StorageType.SQLITE
    
    # SQLite 配置
    sqlite_path: str = "data/agent_hive.db"
    
    # MySQL 配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "agent_hive"
    
    # PostgreSQL 配置
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_database: str = "agent_hive"
    
    # 连接池配置
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    
    # 其他配置
    echo_sql: bool = False  # 是否打印 SQL 语句（调试用）
    auto_create_tables: bool = True  # 是否自动创建表
    
    @classmethod
    def from_env(cls) -> "StorageConfig":
        """从环境变量加载配置"""
        storage_type_str = os.getenv("STORAGE_TYPE", "sqlite").lower()
        
        try:
            storage_type = StorageType(storage_type_str)
        except ValueError:
            print(f"[StorageConfig] Unknown storage type: {storage_type_str}, using sqlite")
            storage_type = StorageType.SQLITE
        
        return cls(
            storage_type=storage_type,
            
            # SQLite
            sqlite_path=os.getenv("SQLITE_PATH", "data/agent_hive.db"),
            
            # MySQL
            mysql_host=os.getenv("MYSQL_HOST", "localhost"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_user=os.getenv("MYSQL_USER", "root"),
            mysql_password=os.getenv("MYSQL_PASSWORD", ""),
            mysql_database=os.getenv("MYSQL_DATABASE", "agent_hive"),
            
            # PostgreSQL
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_user=os.getenv("POSTGRES_USER", "postgres"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
            postgres_database=os.getenv("POSTGRES_DATABASE", "agent_hive"),
            
            # 连接池
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            
            # 其他
            echo_sql=os.getenv("DB_ECHO_SQL", "false").lower() == "true",
            auto_create_tables=os.getenv("DB_AUTO_CREATE_TABLES", "true").lower() == "true",
        )
    
    def get_connection_url(self) -> str:
        """获取数据库连接 URL"""
        if self.storage_type == StorageType.SQLITE:
            return f"sqlite:///{self.sqlite_path}"
        elif self.storage_type == StorageType.MYSQL:
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        elif self.storage_type == StorageType.POSTGRESQL:
            return (
                f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
        elif self.storage_type == StorageType.MEMORY:
            return "sqlite:///:memory:"
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def __repr__(self) -> str:
        return f"StorageConfig(type={self.storage_type.value}, url={self._safe_url()})"
    
    def _safe_url(self) -> str:
        """返回安全的 URL（隐藏密码）"""
        url = self.get_connection_url()
        # 简单隐藏密码
        if "@" in url and ":" in url:
            parts = url.split("@")
            if len(parts) == 2:
                auth_part = parts[0]
                if ":" in auth_part:
                    prefix = auth_part.rsplit(":", 1)[0]
                    return f"{prefix}:***@{parts[1]}"
        return url
