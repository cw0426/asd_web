"""
应用配置
"""
import os
from pathlib import Path

# 项目根目录 (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# asd_beats 项目路径 (与 asd_web 同级)
ASD_BEATS_PATH = BASE_DIR.parent.parent / "asd_beats"

# 数据存储路径
UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = UPLOAD_DIR / "models"
DATA_DIR = UPLOAD_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

# BEATs 预训练模型路径
BEATS_CHECKPOINT = ASD_BEATS_PATH / "BEATs_model" / "BEATs_iter3.pt"

# 数据库配置
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'asd_web.db'}"

# 文件上传配置
MAX_UPLOAD_SIZE = 1500 * 1024 * 1024  # 1.5GB (eval.npy 约为 940MB)
ALLOWED_MODEL_EXTENSIONS = {".pth", ".pt"}
ALLOWED_DATA_EXTENSIONS = {".npy"}

# 默认检测参数
DEFAULT_CONFIG = {
    "crop_time": 4.096,
    "num_crops": 5,
    "batch_size": 25,
    "mel_bins": 128,
    "hop_size": 512,
    "embedding_dim": 768,
    "norm_method": "mean_std",
    "pooling_method": "FMQAP",
    "query": 24,
}

# 机器类型列表 - DCASE 2023
MACHINE_TYPES_DEV = ["ToyCar", "ToyTrain", "bearing", "fan", "gearbox", "slider", "valve"]
MACHINE_TYPES_ADD = ["bandsaw", "grinder", "shaker", "ToyDrone", "ToyNscale", "ToyTank", "Vacuum"]
MACHINE_TYPES_ALL = MACHINE_TYPES_DEV + MACHINE_TYPES_ADD
