"""
memU 适配器实现

BaseMemoryAdapter - 抽象基类
LocalMemUAdapter - 本地 SDK 模式
CloudMemUAdapter - 云端 API 模式
NullMemoryAdapter - 空实现（降级方案）
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from memory.config import MemoryConfig

logger = logging.getLogger(__name__)


class BaseMemoryAdapter(ABC):
    """记忆存储适配器抽象基类"""
    
    @abstractmethod
    async def memorize(
        self,
        user_id: str,
        content: str,
        modality: str = "conversation",
    ) -> Dict[str, Any]:
        """摄入记忆
        
        Args:
            user_id: 用户 ID
            content: 要摄入的内容
            modality: 内容类型 (conversation/document/image/video/audio)
            
        Returns:
            摄入结果（items, categories 等）
        """
        ...
    
    @abstractmethod
    async def retrieve(
        self,
        user_id: str,
        queries: List[str],
        method: str = "rag",
    ) -> Dict[str, Any]:
        """检索记忆
        
        Args:
            user_id: 用户 ID
            queries: 查询列表
            method: 检索方法 (rag/llm)
            
        Returns:
            检索结果（items, categories, resources 等）
        """
        ...
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化适配器，返回是否成功"""
        ...


class NullMemoryAdapter(BaseMemoryAdapter):
    """空实现 - memU 不可用时的降级方案
    
    所有操作静默返回空结果，不影响核心功能
    """
    
    async def memorize(self, user_id: str, content: str, modality: str = "conversation") -> Dict[str, Any]:
        return {"items": [], "categories": [], "status": "disabled"}
    
    async def retrieve(self, user_id: str, queries: List[str], method: str = "rag") -> Dict[str, Any]:
        return {"items": [], "categories": [], "resources": [], "status": "disabled"}
    
    async def initialize(self) -> bool:
        logger.info("[NullMemoryAdapter] Memory system disabled")
        return True


class LocalMemUAdapter(BaseMemoryAdapter):
    """本地 SDK 模式 - 直接调用 memu Python SDK
    
    需要 `pip install memu` 并配置 LLM 和数据库
    """
    
    def __init__(self, config: MemoryConfig):
        self._config = config
        self._service = None
    
    async def initialize(self) -> bool:
        """初始化 memU SDK"""
        try:
            from memu import MemUService
            
            llm_profiles = {
                "default": {
                    "base_url": self._config.llm_base_url,
                    "api_key": self._config.llm_api_key,
                    "chat_model": self._config.llm_chat_model,
                    "embed_model": self._config.llm_embed_model,
                    "client_backend": self._config.llm_client_backend,
                },
            }
            
            database_config = {
                "metadata_store": {"provider": self._config.db_provider},
            }
            
            if self._config.db_provider == "postgresql" and self._config.db_connection_url:
                database_config["metadata_store"]["connection_url"] = self._config.db_connection_url
            
            self._service = MemUService(
                llm_profiles=llm_profiles,
                database_config=database_config,
            )
            
            logger.info("[LocalMemUAdapter] Initialized successfully")
            return True
        except ImportError:
            logger.error("[LocalMemUAdapter] memu package not installed. Run: pip install memu")
            return False
        except Exception as e:
            logger.error(f"[LocalMemUAdapter] Initialization failed: {e}")
            return False
    
    async def memorize(self, user_id: str, content: str, modality: str = "conversation") -> Dict[str, Any]:
        if not self._service:
            return {"items": [], "categories": [], "status": "not_initialized"}
        
        try:
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                result = await self._service.memorize(
                    resource_url=temp_path,
                    modality=modality,
                    user={"user_id": user_id},
                )
                return {
                    "items": result.get("items", []) if isinstance(result, dict) else [],
                    "categories": result.get("categories", []) if isinstance(result, dict) else [],
                    "status": "ok",
                }
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"[LocalMemUAdapter] memorize failed: {e}")
            return {"items": [], "categories": [], "status": "error", "error": str(e)}
    
    async def retrieve(self, user_id: str, queries: List[str], method: str = "rag") -> Dict[str, Any]:
        if not self._service:
            return {"items": [], "categories": [], "resources": [], "status": "not_initialized"}
        
        try:
            query_messages = [
                {"role": "user", "content": {"text": q}} for q in queries
            ]
            
            result = await self._service.retrieve(
                queries=query_messages,
                where={"user_id": user_id},
                method=method,
            )
            
            return {
                "items": result.get("items", []) if isinstance(result, dict) else [],
                "categories": result.get("categories", []) if isinstance(result, dict) else [],
                "resources": result.get("resources", []) if isinstance(result, dict) else [],
                "next_step_query": result.get("next_step_query", "") if isinstance(result, dict) else "",
                "status": "ok",
            }
        except Exception as e:
            logger.error(f"[LocalMemUAdapter] retrieve failed: {e}")
            return {"items": [], "categories": [], "resources": [], "status": "error", "error": str(e)}


class CloudMemUAdapter(BaseMemoryAdapter):
    """云端 API 模式 - 通过 HTTP 调用 api.memu.so"""
    
    def __init__(self, config: MemoryConfig):
        self._config = config
        self._client = None
    
    async def initialize(self) -> bool:
        """初始化 HTTP 客户端"""
        try:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self._config.cloud_base_url,
                headers={
                    "Authorization": f"Bearer {self._config.cloud_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._config.memorize_timeout,
            )
            logger.info(f"[CloudMemUAdapter] Initialized with base_url: {self._config.cloud_base_url}")
            return True
        except Exception as e:
            logger.error(f"[CloudMemUAdapter] Initialization failed: {e}")
            return False
    
    async def memorize(self, user_id: str, content: str, modality: str = "conversation") -> Dict[str, Any]:
        if not self._client:
            return {"items": [], "categories": [], "status": "not_initialized"}
        
        try:
            response = await self._client.post(
                "/api/v3/memory/memorize",
                json={
                    "content": content,
                    "modality": modality,
                    "user": {"user_id": user_id},
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[CloudMemUAdapter] memorize failed: {e}")
            return {"items": [], "categories": [], "status": "error", "error": str(e)}
    
    async def retrieve(self, user_id: str, queries: List[str], method: str = "rag") -> Dict[str, Any]:
        if not self._client:
            return {"items": [], "categories": [], "resources": [], "status": "not_initialized"}
        
        try:
            query_messages = [
                {"role": "user", "content": {"text": q}} for q in queries
            ]
            
            response = await self._client.post(
                "/api/v3/memory/retrieve",
                json={
                    "queries": query_messages,
                    "where": {"user_id": user_id},
                    "method": method,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[CloudMemUAdapter] retrieve failed: {e}")
            return {"items": [], "categories": [], "resources": [], "status": "error", "error": str(e)}
