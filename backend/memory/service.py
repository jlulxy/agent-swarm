"""
MemoryService - 统一记忆服务接口

提供 memorize（摄入）和 retrieve（检索）两个核心方法
通过工厂方法根据配置创建对应的 adapter
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from memory.config import MemoryConfig
from memory.adapters import BaseMemoryAdapter, NullMemoryAdapter, LocalMemUAdapter, CloudMemUAdapter
from memory.builtin_adapter import BuiltinMemoryAdapter

logger = logging.getLogger(__name__)


class MemoryService:
    """统一记忆服务
    
    封装 memU 的 memorize 和 retrieve 操作。
    自动根据配置选择本地 SDK 或云端 API 模式。
    出错时静默降级为 NullAdapter，不影响核心功能。
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self._config = config or MemoryConfig.from_env()
        self._adapter: BaseMemoryAdapter = NullMemoryAdapter()
        self._initialized = False
    
    async def initialize(self):
        """初始化记忆服务"""
        if self._initialized:
            return
        
        mode = self._config.mode
        
        if mode == "disabled":
            self._adapter = NullMemoryAdapter()
            await self._adapter.initialize()
            logger.info("[MemoryService] Memory system disabled")
        
        elif mode == "local":
            # 优先使用内置适配器（SQLite + LLM），不依赖外部 memu SDK
            adapter = BuiltinMemoryAdapter(self._config)
            success = await adapter.initialize()
            if success:
                self._adapter = adapter
                logger.info("[MemoryService] Using builtin memory adapter (SQLite + LLM)")
            else:
                self._adapter = NullMemoryAdapter()
                await self._adapter.initialize()
                logger.warning("[MemoryService] Builtin memory adapter failed, falling back to NullAdapter")
        
        elif mode == "cloud":
            adapter = CloudMemUAdapter(self._config)
            success = await adapter.initialize()
            if success:
                self._adapter = adapter
                logger.info("[MemoryService] Using cloud memU API")
            else:
                self._adapter = NullMemoryAdapter()
                await self._adapter.initialize()
                logger.warning("[MemoryService] Cloud memU failed, falling back to NullAdapter")
        
        else:
            logger.warning(f"[MemoryService] Unknown mode '{mode}', using disabled")
            self._adapter = NullMemoryAdapter()
            await self._adapter.initialize()
        
        self._initialized = True
    
    async def memorize(
        self,
        user_id: str,
        content: str,
        modality: str = "conversation",
    ) -> Dict[str, Any]:
        """摄入记忆（异步安全，出错不抛异常）
        
        Args:
            user_id: 用户 ID
            content: 摄入内容
            modality: 内容类型
            
        Returns:
            摄入结果
        """
        if not self._initialized:
            await self.initialize()
        
        if not user_id or not content:
            return {"items": [], "status": "skipped"}
        
        try:
            return await asyncio.wait_for(
                self._adapter.memorize(user_id, content, modality),
                timeout=self._config.memorize_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[MemoryService] memorize timeout for user {user_id[:8]}...")
            return {"items": [], "status": "timeout"}
        except Exception as e:
            logger.error(f"[MemoryService] memorize error: {e}")
            return {"items": [], "status": "error", "error": str(e)}
    
    async def retrieve(
        self,
        user_id: str,
        queries: List[str],
        method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """检索用户记忆
        
        Args:
            user_id: 用户 ID
            queries: 查询列表
            method: 检索方法 (rag/llm)，默认使用配置值
            
        Returns:
            检索结果
        """
        if not self._initialized:
            await self.initialize()
        
        if not user_id or not queries:
            return {"items": [], "categories": [], "resources": [], "status": "skipped"}
        
        method = method or self._config.retrieve_method
        
        try:
            return await asyncio.wait_for(
                self._adapter.retrieve(user_id, queries, method),
                timeout=self._config.retrieve_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[MemoryService] retrieve timeout for user {user_id[:8]}...")
            return {"items": [], "categories": [], "resources": [], "status": "timeout"}
        except Exception as e:
            logger.error(f"[MemoryService] retrieve error: {e}")
            return {"items": [], "categories": [], "resources": [], "status": "error", "error": str(e)}
    
    def format_for_prompt(self, memories: Dict[str, Any]) -> str:
        """将检索结果格式化为可注入 prompt 的文本
        
        Args:
            memories: retrieve() 的返回值
            
        Returns:
            格式化的文本段落，如果无有效记忆则返回空字符串
        """
        items = memories.get("items", [])
        if not items:
            return ""
        
        parts = ["## 用户偏好与记忆\n"]
        parts.append("以下是该用户的历史偏好和特点，请在执行任务时参考：\n")
        
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                content = item.get("content", item.get("text", str(item)))
            else:
                content = str(item)
            parts.append(f"- {content}")
        
        categories = memories.get("categories", [])
        if categories:
            cat_names = []
            for cat in categories:
                if isinstance(cat, dict):
                    cat_names.append(cat.get("name", str(cat)))
                else:
                    cat_names.append(str(cat))
            parts.append(f"\n关注领域: {', '.join(cat_names)}")
        
        return "\n".join(parts)
    
    @property
    def is_enabled(self) -> bool:
        """记忆服务是否真正可用（配置启用且 adapter 初始化成功）
        
        注意：初始化前基于配置判断（乐观），初始化后基于实际 adapter 判断。
        这确保 Agent 层面的 `if is_enabled: await retrieve()` 能正确触发懒加载。
        """
        if not self._initialized:
            # 尚未初始化：基于配置判断，让调用方走进 retrieve/memorize 触发懒加载
            return self._config.mode != "disabled"
        # 已初始化：基于实际 adapter 类型判断
        return self._config.mode != "disabled" and not isinstance(self._adapter, NullMemoryAdapter)
    
    @property
    def is_configured(self) -> bool:
        """用户是否配置了记忆模式（不论 adapter 是否初始化成功）"""
        return self._config.mode != "disabled"
    
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """删除指定记忆条目
        
        Args:
            user_id: 用户 ID（用于权限校验）
            memory_id: 记忆条目 ID
            
        Returns:
            是否删除成功
        """
        if not self._initialized:
            await self.initialize()
        
        if not hasattr(self._adapter, 'delete_memory'):
            logger.warning("[MemoryService] Current adapter does not support delete_memory")
            return False
        
        try:
            return await self._adapter.delete_memory(user_id, memory_id)
        except Exception as e:
            logger.error(f"[MemoryService] delete_memory error: {e}")
            return False


# 全局单例
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """获取全局 MemoryService 单例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
