"""
SQLAlchemy ORM Models
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Model(Base):
    """模型表"""
    __tablename__ = "models"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    description = Column(Text, default="")

    # 模型参数
    pooling_method = Column(String(64), default="FMQAP")
    query = Column(Integer, default=24)
    embedding_dim = Column(Integer, default=768)
    use_wap = Column(Boolean, default=False)
    wap_method = Column(String(32), default="weighted")
    num_classes = Column(Integer, default=167)

    # 训练信息
    train_dataset = Column(String(32), default="All")
    train_epochs = Column(Integer, default=0)
    loss_func = Column(String(64), default="ArcFace")

    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    tasks = relationship("Task", back_populates="model", cascade="all, delete-orphan")


class DataFile(Base):
    """数据文件表"""
    __tablename__ = "data_files"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    num_samples = Column(Integer, default=0)
    description = Column(Text, default="")

    create_time = Column(DateTime, default=datetime.utcnow)

    # 关联
    tasks = relationship("Task", back_populates="data_file_ref")


class Task(Base):
    """检测任务表"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    model_id = Column(String(36), ForeignKey("models.id"), nullable=False)
    data_file_id = Column(String(36), ForeignKey("data_files.id"), nullable=True)
    data_file = Column(String(512), nullable=False)  # 保留以兼容旧数据
    status = Column(String(32), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    progress_message = Column(String(255), default="")
    error_message = Column(Text, default="")

    # 配置参数 (JSON 字符串)
    config_json = Column(Text, default="{}")

    create_time = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # 关联
    model = relationship("Model", back_populates="tasks")
    data_file_ref = relationship("DataFile", back_populates="tasks")
    result = relationship("Result", back_populates="task", uselist=False, cascade="all, delete-orphan")


class Result(Base):
    """检测结果表"""
    __tablename__ = "results"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    model_id = Column(String(36), ForeignKey("models.id"), nullable=False)

    # 总体指标
    overall = Column(Float, default=0.0)
    auc_source = Column(Float, default=0.0)
    auc_target = Column(Float, default=0.0)
    p_auc = Column(Float, default=0.0)

    # 分类型指标 (JSON 字符串)
    metrics_json = Column(Text, default="{}")

    create_time = Column(DateTime, default=datetime.utcnow)

    # 关联
    task = relationship("Task", back_populates="result")
    sample_results = relationship("SampleResult", back_populates="result", cascade="all, delete-orphan")


class SampleResult(Base):
    """样本检测结果表"""
    __tablename__ = "sample_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(36), ForeignKey("results.id"), nullable=False)

    sample_index = Column(Integer, default=0)
    section = Column(Integer, default=0)
    machine_type = Column(Integer, default=0)
    machine_name = Column(String(64), default="")
    domain = Column(String(32), default="")
    score = Column(Float, default=0.0)
    label = Column(Integer, default=0)
    filename = Column(String(512), default="")

    # 关联
    result = relationship("Result", back_populates="sample_results")
