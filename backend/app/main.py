"""
ASD Web Backend - Main Application

异常音频检测系统后端服务
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import UPLOAD_DIR, MODELS_DIR, DATA_DIR, RESULTS_DIR
from app.db.database import init_db
from app.api import models, tasks, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("Starting ASD Web Backend...")

    # 创建必要的目录
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 初始化数据库
    await init_db()
    print("Database initialized.")

    yield

    # 关闭时
    print("Shutting down ASD Web Backend...")


# 创建 FastAPI 应用
app = FastAPI(
    title="ASD Web API",
    description="异常音频检测系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(models.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(results.router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "ASD Web API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/info")
async def get_system_info():
    """获取系统信息"""
    import torch

    return {
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "pytorch_version": torch.__version__,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=300  # 5分钟连接保持
    )
