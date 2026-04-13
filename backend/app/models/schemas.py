"""
Pydantic schemas for API
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ==================== Model Schemas ====================

class ModelBase(BaseModel):
    """模型基础模式"""
    name: str
    description: str = ""


class ModelCreate(ModelBase):
    """创建模型请求"""
    pooling_method: str = "FMQAP"
    query: int = 24
    embedding_dim: int = 768
    use_wap: bool = False
    wap_method: str = "weighted"
    num_classes: int = 167
    train_dataset: str = "All"
    train_epochs: int = 0
    loss_func: str = "ArcFace"


class ModelUpdate(BaseModel):
    """更新模型请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    pooling_method: Optional[str] = None
    query: Optional[int] = None
    embedding_dim: Optional[int] = None
    use_wap: Optional[bool] = None
    wap_method: Optional[str] = None


class ModelResponse(ModelBase):
    """模型响应"""
    id: str
    file_path: str
    file_size: int
    pooling_method: str
    query: int
    embedding_dim: int
    use_wap: bool
    wap_method: str
    num_classes: int
    train_dataset: str
    train_epochs: int
    loss_func: str
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelListResponse(BaseModel):
    """模型列表响应"""
    total: int
    items: List[ModelResponse]


# ==================== DataFile Schemas ====================

class DataFileCreate(BaseModel):
    """创建数据文件请求"""
    name: str
    description: str = ""


class DataFileResponse(BaseModel):
    """数据文件响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    file_path: str
    file_size: int
    num_samples: int
    description: str
    create_time: datetime


class DataFileListResponse(BaseModel):
    """数据文件列表响应"""
    total: int
    items: List[DataFileResponse]


# ==================== Task Schemas ====================

class TaskConfig(BaseModel):
    """任务配置"""
    crop_time: float = Field(default=4.096, description="裁剪时长(秒)")
    num_crops: int = Field(default=5, description="裁剪数量")
    batch_size: int = Field(default=25, description="批量大小")
    norm_method: str = Field(default="mean_std", description="归一化方法")


class TaskCreate(BaseModel):
    """创建任务请求"""
    model_config = ConfigDict(protected_namespaces=())

    model_id: str
    data_file_id: str  # 使用数据文件ID
    config: TaskConfig = TaskConfig()


class TaskResponse(BaseModel):
    """任务响应"""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    model_id: str
    data_file: str
    status: str
    progress: float
    progress_message: str = ""
    error_message: str
    config: Dict[str, Any]
    create_time: datetime
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    result_id: Optional[str] = None

    @classmethod
    def from_orm_with_config(cls, task, result_id: str = None):
        import json
        return cls(
            id=task.id,
            model_id=task.model_id,
            data_file=task.data_file,
            status=task.status,
            progress=task.progress,
            progress_message=task.progress_message or "",
            error_message=task.error_message,
            config=json.loads(task.config_json),
            create_time=task.create_time,
            start_time=task.start_time,
            end_time=task.end_time,
            result_id=result_id
        )


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    items: List[TaskResponse]


# ==================== Result Schemas ====================

class MetricsByType(BaseModel):
    """分类型指标"""
    auc: float
    pauc: float
    hmean: float


class ResultResponse(BaseModel):
    """检测结果响应"""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    task_id: str
    model_id: str
    overall: float
    auc_source: float
    auc_target: float
    p_auc: float
    metrics_by_type: Dict[str, MetricsByType]
    create_time: datetime

    @classmethod
    def from_orm_with_metrics(cls, result):
        import json
        metrics_raw = json.loads(result.metrics_json)
        metrics_by_type = {
            k: MetricsByType(**v) for k, v in metrics_raw.items()
        }
        return cls(
            id=result.id,
            task_id=result.task_id,
            model_id=result.model_id,
            overall=result.overall,
            auc_source=result.auc_source,
            auc_target=result.auc_target,
            p_auc=result.p_auc,
            metrics_by_type=metrics_by_type,
            create_time=result.create_time
        )


class SampleResultResponse(BaseModel):
    """样本结果响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sample_index: int
    section: int
    machine_type: int
    machine_name: str = ""
    domain: str
    score: float
    label: int
    filename: str


class SampleResultListResponse(BaseModel):
    """样本结果列表响应"""
    total: int
    items: List[SampleResultResponse]


# ==================== Common Schemas ====================

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    status: str = "error"
