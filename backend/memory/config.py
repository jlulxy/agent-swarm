"""
记忆服务配置

从环境变量加载 memU 配置，支持 local / cloud / disabled 三种模式
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class MemoryConfig:
    """记忆服务配置"""
    
    # 模式: local (本地 SDK), cloud (api.memu.so), disabled (关闭)
    mode: str = "disabled"
    
    # 云端 API 配置
    cloud_api_key: str = ""
    cloud_base_url: str = "https://api.memu.so"
    
    # 本地 SDK LLM 配置
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_chat_model: str = ""
    llm_embed_model: str = ""
    llm_client_backend: str = "sdk"
    
    # 本地 SDK 数据库配置
    db_provider: str = "inmemory"  # inmemory / postgresql
    db_connection_url: str = ""
    
    # 检索配置
    retrieve_method: str = "rag"  # rag / llm
    retrieve_timeout: float = 5.0  # 超时时间（秒）
    
    # 记忆摄入配置
    memorize_timeout: float = 30.0  # 摄入超时
    
    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """从环境变量加载配置"""
        return cls(
            mode=os.getenv("MEMU_MODE", "disabled").lower(),
            cloud_api_key=os.getenv("MEMU_API_KEY", ""),
            cloud_base_url=os.getenv("MEMU_BASE_URL", "https://api.memu.so"),
            llm_base_url=os.getenv("MEMU_LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "")),
            llm_api_key=os.getenv("MEMU_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            llm_chat_model=os.getenv("MEMU_LLM_CHAT_MODEL", "gpt-4o-mini"),
            llm_embed_model=os.getenv("MEMU_LLM_EMBED_MODEL", "text-embedding-3-small"),
            llm_client_backend=os.getenv("MEMU_LLM_CLIENT_BACKEND", "sdk"),
            db_provider=os.getenv("MEMU_DB_PROVIDER", "inmemory"),
            db_connection_url=os.getenv("MEMU_DB_URL", ""),
            retrieve_method=os.getenv("MEMU_RETRIEVE_METHOD", "rag"),
            retrieve_timeout=float(os.getenv("MEMU_RETRIEVE_TIMEOUT", "5.0")),
            memorize_timeout=float(os.getenv("MEMU_MEMORIZE_TIMEOUT", "30.0")),
        )
