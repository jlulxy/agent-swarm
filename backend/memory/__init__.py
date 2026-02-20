"""
记忆模块 - memU 集成层

提供统一的记忆摄入和检索接口，支持本地 SDK 和云端 API 两种模式
"""

from memory.service import MemoryService, get_memory_service

__all__ = [
    "MemoryService",
    "get_memory_service",
]
