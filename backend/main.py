"""
Agent Swarm - 主入口

启动 FastAPI 服务，支持 AG-UI 协议
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api import router
from auth.routes import router as auth_router
from skills import init_skills, get_global_registry

# 加载环境变量
load_dotenv()

# 初始化技能系统（v2 架构 - SKILL.md 格式）
def _init_skills():
    """初始化技能系统，加载 SKILL.md 格式的技能库"""
    count = init_skills()
    skill_names = get_global_registry().list_names()
    print(f"    ✅ 已加载 {count} 个技能: {', '.join(skill_names)}")
    return get_global_registry()

skill_registry = _init_skills()

# 创建 FastAPI 应用
app = FastAPI(
    title="Agent Swarm",
    description="""
# 🐝 Agent Swarm API

一个支持**动态角色涌现**和 **3D 编排式协作**的智能 Agent 蜂群协作系统。

## 核心特性

- **角色涌现**: LLM 自主规划，动态生成专业角色
- **3D 编排**: 并行执行 + 动态中继站 + 自适应同步
- **AG-UI 协议**: 完整的实时事件流支持

## 主要接口

- `POST /api/task/stream` - 执行任务（SSE 事件流）
- `POST /api/intervention` - 人工干预
- `GET /api/task/{session_id}/state` - 获取任务状态
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """根路由"""
    return {
        "name": "Agent Swarm",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🐝 Agent Swarm                                           ║
    ║                                                           ║
    ║   角色涌现 × 3D编排 × AG-UI协议                            ║
    ║                                                           ║
    ║   Server: http://{host}:{port}                            ║
    ║   API Docs: http://{host}:{port}/docs                     ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    debug = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
