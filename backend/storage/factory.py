"""
仓库工厂

根据配置创建对应的存储仓库实例
"""

from typing import Optional
from storage.config import StorageConfig, StorageType
from storage.base import BaseSessionRepository


class RepositoryFactory:
    """仓库工厂 - 根据配置创建对应的仓库实例"""
    
    _instance: Optional["RepositoryFactory"] = None
    _repository = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    def get_repository(self, config: Optional[StorageConfig] = None):
        """获取仓库实例（单例）
        
        Args:
            config: 存储配置，如果为 None 则从环境变量加载
        """
        if self._repository is not None:
            return self._repository
        
        if config is None:
            config = StorageConfig.from_env()
        
        if config.storage_type == StorageType.MEMORY:
            # 内存模式（用于测试）
            from storage.memory_repository import MemoryRepository
            self._repository = MemoryRepository()
        else:
            # SQLAlchemy 模式（SQLite、MySQL、PostgreSQL）
            from storage.sqlalchemy_repository import SQLAlchemyRepository
            self._repository = SQLAlchemyRepository(config)
            self._repository.initialize()
        
        print(f"[RepositoryFactory] Created repository: {type(self._repository).__name__}")
        return self._repository
    
    def reset(self):
        """重置仓库（主要用于测试）"""
        self._repository = None


# 全局工厂实例
_factory: Optional[RepositoryFactory] = None


def get_repository(config: Optional[StorageConfig] = None):
    """获取全局仓库实例
    
    这是主要的入口点，用于获取数据访问仓库
    
    Args:
        config: 存储配置，如果为 None 则从环境变量加载
        
    Returns:
        仓库实例（支持所有数据访问接口）
    """
    global _factory
    if _factory is None:
        _factory = RepositoryFactory()
    return _factory.get_repository(config)


def reset_repository():
    """重置全局仓库（用于测试）"""
    global _factory
    if _factory is not None:
        _factory.reset()
