"""
认证相关 API 路由

POST /api/auth/register - 用户注册
POST /api/auth/login - 用户登录
GET /api/auth/me - 获取当前用户信息
PUT /api/auth/me - 更新用户信息
GET /api/auth/memories - 查询用户长期记忆
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query

from auth.provider import AuthProvider
from auth.dependencies import get_auth_provider, get_current_user
from storage.factory import get_repository
from memory.service import get_memory_service


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=64)


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    created_at: str


@router.post("/register", response_model=AuthResponse)
async def register(
    req: RegisterRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """用户注册"""
    credentials = {
        "username": req.username,
        "password": req.password,
        "display_name": req.display_name or req.username,
    }
    
    user = await auth.register(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Username may already exist, or input is invalid.",
        )
    
    token = auth.create_token(user.user_id)
    
    return AuthResponse(
        token=token,
        user={
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        },
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    auth: AuthProvider = Depends(get_auth_provider),
):
    """用户登录"""
    user_id = await auth.authenticate({
        "username": req.username,
        "password": req.password,
    })
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    token = auth.create_token(user_id)
    
    repo = get_repository()
    user = await repo.get_user_by_id(user_id)
    
    return AuthResponse(
        token=token,
        user={
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user),
):
    """获取当前用户信息"""
    repo = get_repository()
    user = await repo.get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UpdateUserRequest,
    user_id: str = Depends(get_current_user),
):
    """更新当前用户信息"""
    repo = get_repository()
    
    updates = {}
    if req.display_name is not None:
        updates["display_name"] = req.display_name
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    user = await repo.update_user(user_id, updates)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/memories")
async def get_user_memories(
    user_id: str = Depends(get_current_user),
    query: Optional[str] = Query(None, description="检索关键词，为空则返回全部记忆"),
):
    """查询用户的长期记忆
    
    返回记忆系统的状态和记忆条目列表。
    即使记忆系统处于 disabled 状态，也会返回状态信息，方便前端展示。
    """
    memory_service = get_memory_service()
    
    # 确保已初始化（懒加载）
    if not memory_service._initialized:
        await memory_service.initialize()
    
    # 区分三种状态：
    # 1. disabled - 用户配置了 MEMU_MODE=disabled
    # 2. degraded - 用户配置了 local/cloud 但 adapter 初始化失败（如缺包）
    # 3. ok - 真正可用
    if not memory_service.is_configured:
        status = "disabled"
    elif not memory_service.is_enabled:
        status = "degraded"
    else:
        status = "ok"
    
    result = {
        "enabled": memory_service.is_enabled,
        "mode": memory_service._config.mode,
        "items": [],
        "categories": [],
        "status": status,
        "message": "" if memory_service.is_enabled else (
            "记忆系统未配置，请在 .env 中设置 MEMU_MODE=local 或 cloud" if not memory_service.is_configured
            else "记忆服务初始化失败（可能缺少 memu 包：pip install memu），已降级为关闭状态"
        ),
    }
    
    if memory_service.is_enabled:
        queries = [query] if query else ["用户偏好和特点"]
        memories = await memory_service.retrieve(
            user_id=user_id,
            queries=queries,
        )
        result["items"] = memories.get("items", [])
        result["categories"] = memories.get("categories", [])
        result["status"] = memories.get("status", "ok")
    
    return result


@router.delete("/memories/{memory_id}")
async def delete_user_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
):
    """删除指定的用户记忆条目
    
    只能删除属于当前用户的记忆，防止越权。
    """
    memory_service = get_memory_service()
    
    if not memory_service.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="记忆系统未启用",
        )
    
    success = await memory_service.delete_memory(user_id, memory_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="记忆不存在或无权删除",
        )
    
    return {"success": True, "message": "记忆已删除"}
