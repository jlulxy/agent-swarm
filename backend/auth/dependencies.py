"""
FastAPI 依赖注入函数

提供 get_current_user 和 get_optional_user 两种依赖：
- get_current_user: 强制认证，未登录返回 401
- get_optional_user: 可选认证，未登录返回 None（兼容匿名访问）
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.provider import AuthProvider, LocalAuthProvider
from storage.factory import get_repository


security = HTTPBearer(auto_error=False)

_auth_provider: Optional[AuthProvider] = None


def get_auth_provider() -> AuthProvider:
    """获取全局 AuthProvider 单例"""
    global _auth_provider
    if _auth_provider is None:
        secret_key = os.getenv("JWT_SECRET", "agent-hive-default-secret-change-me")
        token_expire_hours = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
        repo = get_repository()
        _auth_provider = LocalAuthProvider(
            secret_key=secret_key,
            user_repository=repo,
            token_expire_hours=token_expire_hours,
        )
    return _auth_provider


def reset_auth_provider():
    """重置 AuthProvider（用于测试）"""
    global _auth_provider
    _auth_provider = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth: AuthProvider = Depends(get_auth_provider),
) -> str:
    """强制认证依赖 - 返回 user_id，未登录返回 401"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = auth.verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth: AuthProvider = Depends(get_auth_provider),
) -> Optional[str]:
    """可选认证依赖 - 返回 user_id 或 None（兼容匿名访问）"""
    if credentials is None:
        return None
    
    return auth.verify_token(credentials.credentials)
