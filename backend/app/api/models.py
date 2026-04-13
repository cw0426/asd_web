"""
Model Management API Routes
"""
import os
import uuid
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MODELS_DIR, ALLOWED_MODEL_EXTENSIONS, MAX_UPLOAD_SIZE
from app.db.database import get_db
from app.db import crud
from app.models.schemas import (
    ModelCreate, ModelUpdate, ModelResponse, ModelListResponse,
    MessageResponse
)

router = APIRouter(prefix="/models", tags=["Models"])


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


@router.post("/upload", response_model=ModelResponse)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    pooling_method: str = Form(default="FMQAP"),
    query: int = Form(default=24),
    embedding_dim: int = Form(default=768),
    use_wap: bool = Form(default=False),
    wap_method: str = Form(default="weighted"),
    num_classes: int = Form(default=167),
    train_dataset: str = Form(default="All"),
    train_epochs: int = Form(default=0),
    loss_func: str = Form(default="ArcFace"),
    db: AsyncSession = Depends(get_db)
):
    """
    上传模型文件

    - 支持 .pth, .pt 格式
    - 最大文件大小: 1.5GB
    """
    # 验证文件扩展名
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_MODEL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {ALLOWED_MODEL_EXTENSIONS}"
        )

    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    # 生成唯一文件名
    model_id = str(uuid.uuid4())
    file_name = f"{model_id}{ext}"
    file_path = os.path.join(MODELS_DIR, file_name)

    # 确保目录存在
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据库记录
    model = await crud.create_model(
        db,
        name=name,
        file_path=file_path,
        file_size=len(content),
        description=description,
        pooling_method=pooling_method,
        query=query,
        embedding_dim=embedding_dim,
        use_wap=use_wap,
        wap_method=wap_method,
        num_classes=num_classes,
        train_dataset=train_dataset,
        train_epochs=train_epochs,
        loss_func=loss_func
    )

    return model


@router.get("", response_model=ModelListResponse)
async def list_models(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取模型列表"""
    models = await crud.get_models(db, skip=skip, limit=limit)
    return ModelListResponse(
        total=len(models),
        items=[ModelResponse.model_validate(m) for m in models]
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取模型详情"""
    model = await crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    update_data: ModelUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新模型信息"""
    model = await crud.update_model(
        db,
        model_id,
        **update_data.model_dump(exclude_unset=True)
    )
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.delete("/{model_id}", response_model=MessageResponse)
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除模型"""
    model = await crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 删除文件
    if os.path.exists(model.file_path):
        os.remove(model.file_path)

    # 删除数据库记录
    await crud.delete_model(db, model_id)

    return MessageResponse(message="Model deleted successfully")


@router.post("/{model_id}/validate")
async def validate_model(
    model_id: str,
    db: AsyncSession = Depends(get_db)
):
    """验证模型文件"""
    import torch

    model = await crud.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="Model file not found")

    try:
        # 尝试加载模型
        state = torch.load(model.file_path, map_location="cpu", weights_only=False)

        return {
            "valid": True,
            "keys": list(state.keys()) if isinstance(state, dict) else "state_dict",
            "message": "Model file is valid"
        }
    except Exception as e:
        return {
            "valid": False,
            "message": str(e)
        }
