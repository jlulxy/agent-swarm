"""
内置记忆适配器 - 不依赖外部 memu SDK

使用 SQLite 存储 + OpenAI LLM 提取记忆要点
完全基于项目已有依赖（sqlalchemy, aiosqlite, openai）
"""

import json
import time
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

import sqlalchemy as sa
from sqlalchemy import Column, String, Text, Float, DateTime, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from memory.config import MemoryConfig
from memory.adapters import BaseMemoryAdapter

logger = logging.getLogger(__name__)

Base = declarative_base()


class MemoryItem(Base):
    """记忆条目表"""
    __tablename__ = "memory_items"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(64), default="general")
    source = Column(String(32), default="conversation")  # conversation / manual
    importance = Column(Float, default=0.5)  # 0~1 重要度
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuiltinMemoryAdapter(BaseMemoryAdapter):
    """内置记忆适配器
    
    核心设计：
    1. 存储层：SQLite（复用项目已有依赖）
    2. 摄入：用 LLM 从对话内容中提取关键记忆点（偏好、习惯、特点）
    3. 检索：全量加载用户记忆（内存量级小），按 importance 排序返回
    4. 去重：content hash 去重，相同内容只存一次
    """
    
    def __init__(self, config: MemoryConfig):
        self._config = config
        self._engine = None
        self._session_factory = None
        self._openai_client = None
    
    async def initialize(self) -> bool:
        """初始化 SQLite 存储和 OpenAI client"""
        try:
            import os
            
            # SQLite 存储
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "memories.db")
            
            self._engine = create_engine(
                f"sqlite:///{db_path}",
                echo=False,
                connect_args={"check_same_thread": False},
            )
            Base.metadata.create_all(self._engine)
            self._session_factory = sessionmaker(bind=self._engine)
            
            # OpenAI client（复用项目已有配置）
            from openai import AsyncOpenAI
            
            base_url = self._config.llm_base_url or os.getenv("OPENAI_BASE_URL", "")
            api_key = self._config.llm_api_key or os.getenv("OPENAI_API_KEY", "")
            
            if not api_key:
                logger.error("[BuiltinMemoryAdapter] No API key configured")
                return False
            
            self._openai_client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key,
            )
            
            logger.info(f"[BuiltinMemoryAdapter] Initialized with SQLite: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"[BuiltinMemoryAdapter] Initialization failed: {e}")
            return False
    
    def _content_hash(self, user_id: str, content: str) -> str:
        """内容指纹，用于去重"""
        return hashlib.md5(f"{user_id}:{content.strip().lower()}".encode()).hexdigest()
    
    async def _extract_memories(self, content: str) -> List[Dict[str, str]]:
        """用 LLM 从对话内容中提取记忆要点"""
        if not self._openai_client:
            return []
        
        model = self._config.llm_chat_model or "gpt-4o-mini"
        
        try:
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个**用户画像提取器**。你的目标是从用户的发言中，提取关于**用户本人**的长期画像信息。\n\n"
                            "## 提取维度（按优先级排序）\n\n"
                            "### 1. identity（身份）— 最高优先级\n"
                            "用户自述的姓名、称呼、昵称、年龄、性别、所在地等个人身份信息。\n"
                            "例：'用户名叫小明'、'用户在深圳'、'用户希望被称为老李'\n"
                            "**只要用户说了自己的名字/称呼，必须提取。**\n\n"
                            "### 2. background（背景）\n"
                            "职业、角色、所在团队/公司/行业、正在做的项目。\n"
                            "例：'AI后台工程师'、'在做多Agent协作系统'、'在腾讯工作'\n\n"
                            "### 3. preference（偏好）\n"
                            "用户明确表达的喜好、风格倾向、技术选型偏好。\n"
                            "例：'偏好用Python'、'喜欢简洁的代码风格'、'偏好React'\n\n"
                            "### 4. skill（技能）\n"
                            "用户展现出的专业技能、擅长领域。\n"
                            "例：'熟悉分布式系统'、'有后端架构经验'\n\n"
                            "### 5. workflow（工作流）\n"
                            "用户的工作习惯、协作方式、流程偏好。\n"
                            "例：'习惯先设计再编码'、'喜欢模块化架构'\n\n"
                            "### 6. personality（特点）\n"
                            "用户的思维方式、沟通风格、价值观。\n"
                            "例：'注重系统级思维'、'追求极致性能'\n\n"
                            "## 不要提取\n"
                            "- ❌ Agent/AI 的分析结论、发现、研究结果\n"
                            "- ❌ 任务的具体执行结果、数据分析结论\n"
                            "- ❌ 系统/工具的状态信息\n\n"
                            "## 质量要求\n"
                            "- 每条记忆必须是关于**用户本人**的信息\n"
                            "- 用户主动提及的个人信息（名字、背景等）优先级最高，必须提取\n"
                            "- 每条用简洁的一句话概括\n"
                            "- 如果内容中确实没有任何用户信息，返回空数组 []\n\n"
                            "返回 JSON 数组格式：\n"
                            '[{"content": "画像信息", "category": "分类", "importance": 0.8}]\n'
                            "category 可选：identity / background / preference / skill / workflow / personality\n"
                            "importance: 0.6~1.0，identity 类固定为 0.95，其他越稳定越高"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"请从以下用户发言中提取用户画像信息（重点关注用户自我介绍、身份信息、偏好表达）：\n\n{content[:3000]}",
                    },
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            text = response.choices[0].message.content.strip()
            # 尝试解析 JSON
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            items = json.loads(text)
            if isinstance(items, list):
                return items
            return []
            
        except Exception as e:
            logger.warning(f"[BuiltinMemoryAdapter] Memory extraction failed: {e}")
            return []
    
    async def memorize(
        self,
        user_id: str,
        content: str,
        modality: str = "conversation",
    ) -> Dict[str, Any]:
        """摄入记忆：LLM 提取要点 → 去重 → 存入 SQLite"""
        if not self._session_factory:
            return {"items": [], "categories": [], "status": "not_initialized"}
        
        try:
            # LLM 提取记忆要点
            extracted = await self._extract_memories(content)
            
            if not extracted:
                return {"items": [], "categories": [], "status": "ok", "message": "no memorable content"}
            
            saved_items = []
            with self._session_factory() as session:
                for item in extracted:
                    item_content = item.get("content", "").strip()
                    if not item_content:
                        continue
                    
                    item_id = self._content_hash(user_id, item_content)
                    
                    # 去重：已存在则跳过
                    existing = session.query(MemoryItem).filter_by(id=item_id).first()
                    if existing:
                        existing.access_count += 1
                        existing.updated_at = datetime.utcnow()
                        continue
                    
                    memory = MemoryItem(
                        id=item_id,
                        user_id=user_id,
                        content=item_content,
                        category=item.get("category", "general"),
                        source=modality,
                        importance=min(1.0, max(0.0, float(item.get("importance", 0.5)))),
                    )
                    session.add(memory)
                    saved_items.append({
                        "content": item_content,
                        "category": item.get("category", "general"),
                    })
                
                session.commit()
            
            logger.info(f"[BuiltinMemoryAdapter] Saved {len(saved_items)} memories for user {user_id[:8]}...")
            
            return {
                "items": saved_items,
                "categories": list(set(i["category"] for i in saved_items)),
                "status": "ok",
            }
            
        except Exception as e:
            logger.error(f"[BuiltinMemoryAdapter] memorize failed: {e}")
            return {"items": [], "categories": [], "status": "error", "error": str(e)}
    
    async def retrieve(
        self,
        user_id: str,
        queries: List[str],
        method: str = "rag",
    ) -> Dict[str, Any]:
        """检索记忆：从 SQLite 加载用户所有记忆，按 importance 排序"""
        if not self._session_factory:
            return {"items": [], "categories": [], "resources": [], "status": "not_initialized"}
        
        try:
            with self._session_factory() as session:
                memories = (
                    session.query(MemoryItem)
                    .filter_by(user_id=user_id)
                    .order_by(MemoryItem.importance.desc(), MemoryItem.updated_at.desc())
                    .limit(50)
                    .all()
                )
                
                items = []
                categories = set()
                for m in memories:
                    items.append({
                        "id": m.id,
                        "content": m.content,
                        "category": m.category,
                        "importance": m.importance,
                        "created_at": m.created_at.isoformat() if m.created_at else "",
                    })
                    categories.add(m.category)
                    
                    # 更新访问计数
                    m.access_count += 1
                
                session.commit()
            
            return {
                "items": items,
                "categories": [{"name": c} for c in categories],
                "resources": [],
                "status": "ok",
            }
            
        except Exception as e:
            logger.error(f"[BuiltinMemoryAdapter] retrieve failed: {e}")
            return {"items": [], "categories": [], "resources": [], "status": "error", "error": str(e)}
    
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """删除指定记忆条目（校验 user_id 防止越权）"""
        if not self._session_factory:
            return False
        
        try:
            with self._session_factory() as session:
                item = session.query(MemoryItem).filter_by(id=memory_id, user_id=user_id).first()
                if not item:
                    return False
                session.delete(item)
                session.commit()
            
            logger.info(f"[BuiltinMemoryAdapter] Deleted memory {memory_id[:8]}... for user {user_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"[BuiltinMemoryAdapter] delete_memory failed: {e}")
            return False
