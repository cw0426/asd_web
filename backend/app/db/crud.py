"""
CRUD operations for database
"""
import json
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model import Model, Task, Result, SampleResult, DataFile


# ==================== Model CRUD ====================

async def create_model(
    db: AsyncSession,
    name: str,
    file_path: str,
    file_size: int = 0,
    description: str = "",
    **kwargs
) -> Model:
    """创建模型记录"""
    model = Model(
        id=str(uuid4()),
        name=name,
        file_path=file_path,
        file_size=file_size,
        description=description,
        **kwargs
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def get_model(db: AsyncSession, model_id: str) -> Optional[Model]:
    """获取单个模型"""
    result = await db.execute(select(Model).where(Model.id == model_id))
    return result.scalar_one_or_none()


async def get_models(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Model]:
    """获取模型列表"""
    result = await db.execute(
        select(Model)
        .order_by(Model.create_time.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_model(db: AsyncSession, model_id: str, **kwargs) -> Optional[Model]:
    """更新模型"""
    model = await get_model(db, model_id)
    if model:
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        model.update_time = datetime.utcnow()
        await db.commit()
        await db.refresh(model)
    return model


async def delete_model(db: AsyncSession, model_id: str) -> bool:
    """删除模型"""
    model = await get_model(db, model_id)
    if model:
        await db.delete(model)
        await db.commit()
        return True
    return False


# ==================== DataFile CRUD ====================

async def create_data_file(
    db: AsyncSession,
    name: str,
    file_path: str,
    file_size: int = 0,
    num_samples: int = 0,
    description: str = ""
) -> DataFile:
    """创建数据文件记录"""
    data_file = DataFile(
        id=str(uuid4()),
        name=name,
        file_path=file_path,
        file_size=file_size,
        num_samples=num_samples,
        description=description
    )
    db.add(data_file)
    await db.commit()
    await db.refresh(data_file)
    return data_file


async def get_data_file(db: AsyncSession, data_file_id: str) -> Optional[DataFile]:
    """获取单个数据文件"""
    result = await db.execute(select(DataFile).where(DataFile.id == data_file_id))
    return result.scalar_one_or_none()


async def get_data_files(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[DataFile]:
    """获取数据文件列表"""
    result = await db.execute(
        select(DataFile)
        .order_by(DataFile.create_time.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def delete_data_file(db: AsyncSession, data_file_id: str) -> bool:
    """删除数据文件"""
    data_file = await get_data_file(db, data_file_id)
    if data_file:
        # 删除物理文件
        import os
        if os.path.exists(data_file.file_path):
            os.remove(data_file.file_path)
        await db.delete(data_file)
        await db.commit()
        return True
    return False


# ==================== Task CRUD ====================

async def create_task(
    db: AsyncSession,
    model_id: str,
    data_file: str,
    data_file_id: str = None,
    config: dict = None
) -> Task:
    """创建检测任务"""
    task = Task(
        id=str(uuid4()),
        model_id=model_id,
        data_file=data_file,
        data_file_id=data_file_id,
        config_json=json.dumps(config or {})
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    """获取单个任务"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_task_with_result(db: AsyncSession, task_id: str) -> Tuple[Optional[Task], Optional[str]]:
    """获取单个任务及其结果ID（预加载result关系）"""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.result))
    )
    task = result.scalar_one_or_none()
    if task:
        result_id = task.result.id if task.result else None
        return task, result_id
    return None, None


async def get_tasks(
    db: AsyncSession,
    status: str = None,
    skip: int = 0,
    limit: int = 100
) -> List[Task]:
    """获取任务列表"""
    query = select(Task).order_by(Task.create_time.desc())
    if status:
        query = query.where(Task.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_tasks_with_results(
    db: AsyncSession,
    status: str = None,
    skip: int = 0,
    limit: int = 100
) -> List[Tuple[Task, Optional[str]]]:
    """获取任务列表及其结果ID（预加载result关系）"""
    query = select(Task).order_by(Task.create_time.desc())
    if status:
        query = query.where(Task.status == status)
    query = query.options(selectinload(Task.result)).offset(skip).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [(task, task.result.id if task.result else None) for task in tasks]


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    progress: float = None,
    progress_message: str = None,
    error_message: str = None
) -> Optional[Task]:
    """更新任务状态"""
    task = await get_task(db, task_id)
    if task:
        task.status = status
        if progress is not None:
            task.progress = progress
        if progress_message is not None:
            task.progress_message = progress_message
        if error_message is not None:
            task.error_message = error_message
        if status == "running":
            task.start_time = datetime.utcnow()
        elif status in ["completed", "failed"]:
            task.end_time = datetime.utcnow()
        await db.commit()
        await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    """删除任务及其关联的结果"""
    task = await get_task(db, task_id)
    if task:
        await db.delete(task)
        await db.commit()
        return True
    return False


# ==================== Result CRUD ====================

async def create_result(
    db: AsyncSession,
    task_id: str,
    model_id: str,
    overall: float,
    auc_source: float,
    auc_target: float,
    p_auc: float,
    metrics_by_type: dict = None
) -> Result:
    """创建检测结果"""
    result = Result(
        id=str(uuid4()),
        task_id=task_id,
        model_id=model_id,
        overall=overall,
        auc_source=auc_source,
        auc_target=auc_target,
        p_auc=p_auc,
        metrics_json=json.dumps(metrics_by_type or {})
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def get_result(db: AsyncSession, result_id: str) -> Optional[Result]:
    """获取单个结果"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    return result.scalar_one_or_none()


async def get_result_by_task(db: AsyncSession, task_id: str) -> Optional[Result]:
    """根据任务ID获取结果"""
    result = await db.execute(select(Result).where(Result.task_id == task_id))
    return result.scalar_one_or_none()


# ==================== SampleResult CRUD ====================

async def create_sample_results(
    db: AsyncSession,
    result_id: str,
    samples: List[dict]
) -> List[SampleResult]:
    """批量创建样本结果"""
    sample_results = []
    for sample in samples:
        sr = SampleResult(
            result_id=result_id,
            sample_index=sample.get("index", 0),
            section=sample.get("section", 0),
            machine_type=sample.get("machine_type", 0),
            machine_name=sample.get("machine_name", ""),
            domain=sample.get("domain", ""),
            score=sample.get("score", 0.0),
            label=sample.get("label", 0),
            filename=sample.get("filename", "")
        )
        sample_results.append(sr)
        db.add(sr)
    await db.commit()
    return sample_results


async def get_sample_results(
    db: AsyncSession,
    result_id: str,
    skip: int = 0,
    limit: int = 100,
    machine_type: int = None
) -> List[SampleResult]:
    """获取样本结果列表"""
    query = select(SampleResult).where(SampleResult.result_id == result_id)
    if machine_type is not None:
        query = query.where(SampleResult.machine_type == machine_type)
    query = query.order_by(SampleResult.sample_index).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
