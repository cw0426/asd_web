"""
Detection Task API Routes
"""
import os
import json
import uuid
import asyncio
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DATA_DIR, ALLOWED_DATA_EXTENSIONS, MAX_UPLOAD_SIZE, ASD_BEATS_PATH
from app.db.database import get_db
from app.db import crud
from app.models.schemas import (
    TaskCreate, TaskResponse, TaskListResponse,
    MessageResponse, DataFileResponse, DataFileListResponse
)
from app.core.detector import DetectionEngine, DetectionConfig

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()


async def _update_progress(task_id: str, progress: float, message: str):
    """异步更新任务进度到数据库"""
    from app.db.database import async_session
    async with async_session() as db:
        await crud.update_task_status(db, task_id, "running", progress=progress, progress_message=message)
        await db.close()
    print(f"[Task {task_id}] Progress: {progress:.2%} - {message}")


async def run_detection_task(task_id: str, model_id: str, data_file: str, config: dict):
    """后台执行检测任务"""
    from app.db.database import async_session

    async with async_session() as db:
        try:
            # 更新任务状态为运行中
            await crud.update_task_status(db, task_id, "running", progress=0.0)

            # 获取模型信息
            model = await crud.get_model(db, model_id)
            if not model:
                raise ValueError("Model not found")

            # 创建检测配置 - 与 run_eval.sh 参数一致
            detection_config = DetectionConfig(
                crop_time=config.get("crop_time", 4.096),
                num_crops=config.get("num_crops", 5),
                batch_size=config.get("batch_size", 64),
                mel_bins=128,
                hop_size=512,
                embedding_dim=model.embedding_dim,
                norm_method=config.get("norm_method", "mean_std"),
                pooling_method=model.pooling_method,
                query=model.query,
                use_wap=model.use_wap,
                wap_method=model.wap_method,
                num_classes=model.num_classes,
                ckpt_path=model.file_path,  # 用于加载 stat.pth
            )

            # 创建检测引擎
            engine = DetectionEngine()

            # 加载模型
            if not engine.load_model(model.file_path, detection_config):
                raise ValueError("Failed to load model")

            # 获取当前事件循环，用于在线程中调度异步任务
            loop = asyncio.get_event_loop()

            # 定义进度回调 - 在同步线程中调用，通过 run_coroutine_threadsafe 更新 DB
            def progress_callback(progress: float, message: str):
                asyncio.run_coroutine_threadsafe(
                    _update_progress(task_id, progress, message), loop
                )

            # 训练数据路径 (使用 add.npy 作为 reference)
            train_data_path = os.path.join(ASD_BEATS_PATH, "data", "add.npy")

            # 在线程池中执行同步的 run_detection，避免阻塞事件循环
            # Python 3.8 没有 asyncio.to_thread，使用 loop.run_in_executor 替代
            result = await loop.run_in_executor(
                None,
                lambda: engine.run_detection(
                    test_data_path=data_file,
                    train_data_path=train_data_path,
                    progress_callback=progress_callback
                )
            )

            # 检测完成后刷新 db 会话（长时间运行后可能过期）
            try:
                await db.commit()
            except Exception:
                await db.rollback()

            # 保存结果
            db_result = await crud.create_result(
                db,
                task_id=task_id,
                model_id=model_id,
                overall=result.overall,
                auc_source=result.auc_source,
                auc_target=result.auc_target,
                p_auc=result.p_auc,
                metrics_by_type=result.metrics_by_type
            )

            # 保存样本结果
            if result.sample_scores:
                await crud.create_sample_results(
                    db,
                    result_id=db_result.id,
                    samples=result.sample_scores
                )

            # 更新任务状态为完成
            await crud.update_task_status(db, task_id, "completed", progress=1.0)

        except Exception as e:
            # 更新任务状态为失败
            await crud.update_task_status(
                db, task_id, "failed",
                error_message=str(e)
            )
            raise


@router.post("/upload-data", response_model=DataFileResponse)
async def upload_data(
    file: UploadFile = File(...),
    description: str = Form(default=""),
    db: AsyncSession = Depends(get_db)
):
    """
    上传测试数据文件

    - 支持 .npy 格式
    - 最大文件大小: 1.5GB
    - 上传后文件信息保存到数据库，可重复使用
    """
    # 验证文件扩展名
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_DATA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {ALLOWED_DATA_EXTENSIONS}"
        )

    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{ext}"
    file_path = os.path.join(DATA_DIR, file_name)

    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 分块保存文件，避免内存问题
    total_size = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024 * 10)  # 10MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    # 超过大小限制，删除已写入的文件
                    f.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE / 1024 / 1024}MB"
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 验证 npy 文件并获取样本数
    try:
        import numpy as np
        data = np.load(file_path, allow_pickle=True).item()
        num_samples = len(data.get("data", []))
    except Exception as e:
        # 删除无效文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid npy file: {str(e)}")

    # 保存到数据库
    data_file = await crud.create_data_file(
        db,
        name=file.filename,
        file_path=file_path,
        file_size=total_size,
        num_samples=num_samples,
        description=description
    )

    return DataFileResponse.model_validate(data_file)


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    创建检测任务

    - 需要先上传数据文件获取 data_file_id
    - 任务将在后台执行
    """
    # 验证模型存在
    model = await crud.get_model(db, task_data.model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 验证数据文件存在
    data_file = await crud.get_data_file(db, task_data.data_file_id)
    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")

    # 验证物理文件存在
    if not os.path.exists(data_file.file_path):
        raise HTTPException(status_code=400, detail="Data file not found on disk")

    # 创建任务
    task = await crud.create_task(
        db,
        model_id=task_data.model_id,
        data_file_id=task_data.data_file_id,
        data_file=data_file.file_path,
        config=task_data.config.model_dump()
    )

    # 启动后台任务
    background_tasks.add_task(
        run_detection_task,
        task.id,
        task.model_id,
        task.data_file,
        json.loads(task.config_json)
    )

    # 新创建的任务没有结果，result_id 为 None
    return TaskResponse.from_orm_with_config(task, result_id=None)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取任务列表"""
    tasks_with_results = await crud.get_tasks_with_results(db, status=status, skip=skip, limit=limit)
    return TaskListResponse(
        total=len(tasks_with_results),
        items=[TaskResponse.from_orm_with_config(t, result_id=rid) for t, rid in tasks_with_results]
    )


# ==================== Data File Management ====================
# 注意：/data-files 路由必须放在 /{task_id} 之前，否则 FastAPI 会将
# "data-files" 当作 task_id 参数匹配，导致 404 错误

@router.get("/data-files", response_model=DataFileListResponse)
async def list_data_files(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取数据文件列表"""
    data_files = await crud.get_data_files(db, skip=skip, limit=limit)
    return DataFileListResponse(
        total=len(data_files),
        items=[DataFileResponse.model_validate(df) for df in data_files]
    )


@router.get("/data-files/{data_file_id}", response_model=DataFileResponse)
async def get_data_file(
    data_file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取数据文件详情"""
    data_file = await crud.get_data_file(db, data_file_id)
    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")
    return DataFileResponse.model_validate(data_file)


@router.delete("/data-files/{data_file_id}", response_model=MessageResponse)
async def delete_data_file(
    data_file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除数据文件"""
    success = await crud.delete_data_file(db, data_file_id)
    if not success:
        raise HTTPException(status_code=404, detail="Data file not found")
    return MessageResponse(message="Data file deleted successfully")


# ==================== Task Detail & Cancel ====================

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取任务详情"""
    task, result_id = await crud.get_task_with_result(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm_with_config(task, result_id=result_id)


@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """取消任务"""
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    await crud.update_task_status(db, task_id, "cancelled")
    return MessageResponse(message="Task cancelled")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除任务及其结果"""
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 不允许删除正在运行的任务
    if task.status == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a running task")

    success = await crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete task")

    return MessageResponse(message="Task deleted successfully")
