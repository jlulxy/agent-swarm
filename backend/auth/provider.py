"""
认证策略抽象基类和本地实现

设计原则：认证策略（如何验证身份）与用户存储（如何存储用户数据）完全分离。
新增 OAuth/SSO 等登录方式时，只需实现新的 AuthProvider，无需修改用户存储层。
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
import jwt

from storage.base import UserRecord, BaseUserRepository


def _hash_password(password: str) -> str:
    """bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码与 bcrypt 哈希是否匹配"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class AuthProvider(ABC):
    """认证策略抽象基类 - 与用户存储完全解耦
    
    职责：
    - authenticate: 验证凭据，返回 user_id
    - create_token: 为用户创建访问令牌
    - verify_token: 验证令牌，返回 user_id
    
    不负责：
    - 用户数据的 CRUD（由 UserRepository 管理）
    """
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[str]:
        """验证凭据，返回 user_id 或 None"""
        ...
    
    @abstractmethod
    async def register(self, credentials: Dict[str, Any]) -> Optional[UserRecord]:
        """注册新用户，返回 UserRecord 或 None"""
        ...
    
    @abstractmethod
    def create_token(self, user_id: str) -> str:
        """为用户创建访问令牌"""
        ...
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[str]:
        """验证令牌，返回 user_id 或 None"""
        ...


class LocalAuthProvider(AuthProvider):
    """本地用户名密码认证 + JWT
    
    使用 bcrypt 哈希密码，PyJWT 签发/验证 Token。
    Token 中只编码 user_id + exp，足够简洁且可扩展。
    """
    
    def __init__(
        self,
        secret_key: str,
        user_repository: BaseUserRepository,
        token_expire_hours: int = 24,
        algorithm: str = "HS256",
    ):
        self._secret_key = secret_key
        self._user_repo = user_repository
        self._token_expire_hours = token_expire_hours
        self._algorithm = algorithm
    
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[str]:
        """用户名 + 密码验证
        
        credentials: {"username": str, "password": str}
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        
        if not username or not password:
            return None
        
        user = await self._user_repo.get_user_by_username(username)
        if not user:
            return None
        
        if not _verify_password(password, user.password_hash):
            return None
        
        return user.user_id
    
    async def register(self, credentials: Dict[str, Any]) -> Optional[UserRecord]:
        """注册新用户
        
        credentials: {"username": str, "password": str, "display_name": str?}
        """
        username = credentials.get("username", "").strip()
        password = credentials.get("password", "")
        display_name = credentials.get("display_name", "").strip() or username
        
        if not username or not password:
            return None
        
        if len(username) < 2 or len(username) > 32:
            return None
        
        if len(password) < 6:
            return None
        
        existing = await self._user_repo.get_user_by_username(username)
        if existing:
            return None
        
        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password)
        
        record = UserRecord(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            display_name=display_name,
        )
        
        return await self._user_repo.create_user(record)
    
    def create_token(self, user_id: str) -> str:
        """签发 JWT Token"""
        expire = datetime.utcnow() + timedelta(hours=self._token_expire_hours)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
    
    def verify_token(self, token: str) -> Optional[str]:
        """验证 JWT Token，返回 user_id"""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            user_id = payload.get("sub")
            return user_id if user_id else None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
