"""
Model Management API Routes
"""
import os
import uuid
from typing import List, Optional, Tuple
import torch

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


def detect_pooling_method(state_dict: dict) -> Tuple[str, int]:
    """
    根据模型权重自动检测池化方法和输出维度

    Returns:
        tuple: (pooling_method, output_dim)
        - pooling_method: 检测到的池化方法名称
        - output_dim: 池化层输出维度 (用于推断 embedding_dim)

    检测规则:
    - dualdim_scale + scale_weights + linear(1536) → MSDualDimMQAP
    - dualdim_scale + no scale_weights + linear(3072) → MSDualDimMQAP_concat
    - fmqap_scale + scale_weights + linear(1536) → MSFMQAP
    - fmqap_scale + no scale_weights + linear(3072) → MSFMQAP_concat
    - conv_att + conv_freq + linear(1536) → FMQAP
    """
    ebd_keys = [k for k in state_dict.keys() if 'ebd_layer' in k]

    # 检查 Linear 层形状
    linear_key = 'ebd_layer.2.weight'
    if linear_key in state_dict:
        linear_shape = state_dict[linear_key].shape
        # linear_shape = [embedding_dim, input_dim]
        # input_dim: 1536 = 2C (加权融合), 3072 = 4C (concat)
        output_dim = linear_shape[0]  # embedding_dim
        input_dim = linear_shape[1]   # 池化层输出
    else:
        input_dim = 1536
        output_dim = 768

    # 检查是否有 scale_weights
    has_scale_weights = any('scale_weights' in k for k in ebd_keys)

    # 检查是否有 dualdim_scale
    has_dualdim_scale = any('dualdim_scale' in k for k in ebd_keys)

    # 检查是否有 fmqap_scale
    has_fmqap_scale = any('fmqap_scale' in k for k in ebd_keys)

    # 检查是否是基础 FMQAP
    has_conv_att = any('ebd_layer.1.conv_att' == k or 'ebd_layer.1.conv_att' in k for k in ebd_keys)
    has_conv_freq = any('ebd_layer.1.conv_freq.weight' in k for k in ebd_keys)

    # 判断池化方法
    if has_dualdim_scale:
        if has_scale_weights:
            return 'MSDualDimMQAP', output_dim
        else:
            return 'MSDualDimMQAP_concat', output_dim
    elif has_fmqap_scale:
        if has_scale_weights:
            return 'MSFMQAP', output_dim
        else:
            return 'MSFMQAP_concat', output_dim
    elif has_conv_att and has_conv_freq and not has_fmqap_scale and not has_dualdim_scale:
        return 'FMQAP', output_dim
    else:
        # 默认返回 FMQAP
        return 'FMQAP', output_dim


@router.post("/upload", response_model=ModelResponse)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    pooling_method: str = Form(default="auto"),  # 默认自动检测
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
    - pooling_method 设为 "auto" 可自动检测池化方法
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

    # 自动检测池化方法
    detected_pooling = pooling_method
    detected_embedding_dim = embedding_dim

    if pooling_method == "auto" or pooling_method.lower() == "auto":
        try:
            state = torch.load(file_path, map_location="cpu", weights_only=False)
            detected_pooling, detected_embedding_dim = detect_pooling_method(state)
            print(f"[Auto-detect] pooling_method={detected_pooling}, embedding_dim={detected_embedding_dim}")
        except Exception as e:
            print(f"[Auto-detect] Failed: {e}, using default FMQAP")
            detected_pooling = "FMQAP"
            detected_embedding_dim = embedding_dim

    # 创建数据库记录
    model = await crud.create_model(
        db,
        name=name,
        file_path=file_path,
        file_size=len(content),
        description=description,
        pooling_method=detected_pooling,
        query=query,
        embedding_dim=detected_embedding_dim,
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
