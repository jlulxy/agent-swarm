"""
认证模块

提供可扩展的用户认证策略和 FastAPI 依赖注入
"""

from auth.provider import AuthProvider, LocalAuthProvider
from auth.dependencies import get_current_user, get_optional_user, get_auth_provider

__all__ = [
    "AuthProvider",
    "LocalAuthProvider",
    "get_current_user",
    "get_optional_user",
    "get_auth_provider",
]
