"""
Detection Engine - 异常检测引擎

严格参照 asd_beats 项目的 eval.py 和 run_eval.sh 逻辑
"""
import os
import sys
import torch
import numpy as np
from collections import defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 使用 config.py 中定义的 ASD_BEATS_PATH
from app.config import ASD_BEATS_PATH

# 将 asd_beats 目录加入 sys.path，确保能找到其模块
_asd_beats_str = str(ASD_BEATS_PATH)
if _asd_beats_str not in sys.path:
    sys.path.insert(0, _asd_beats_str)

from einops import rearrange
from tqdm import tqdm

# 导入 asd_beats 模块
from Finetune_BEATs import Model_Finetune_BEATs
from dataset_npy import MyDataset_wav_npy, get_dataset_mean_std, get_dataset_test
from wav_transform import LAMTrainTransform
from utils import get_embeddings, compute_scores, score_norm, cal_metrics, cal_mean_std


class _Args:
    """参数对象 - 模块级别定义以确保可被 pickle 序列化（Windows 多进程兼容）"""
    pass


@dataclass
class DetectionConfig:
    """检测配置 - 与 run_eval.sh 中的参数对应"""
    crop_time: float = 4.096
    num_crops: int = 5
    batch_size: int = 64
    mel_bins: int = 128
    hop_size: int = 512
    embedding_dim: int = 768
    norm_method: str = "mean_std"
    pooling_method: str = "FMQAP"
    query: int = 24
    use_wap: bool = False
    wap_method: str = "weighted"
    num_classes: int = 167
    # 检查点路径 - 用于加载 stat.pth (mean_std)
    ckpt_path: str = ""


@dataclass
class DetectionResult:
    """检测结果"""
    overall: float = 0.0
    auc_source: float = 0.0
    auc_target: float = 0.0
    p_auc: float = 0.0
    metrics_by_type: Dict[str, Dict[str, float]] = field(default_factory=dict)
    sample_scores: List[Dict[str, Any]] = field(default_factory=list)


class DetectionEngine:
    """异常检测引擎 - 严格复用 eval.py 的逻辑"""

    # 机器类型映射 - 与 eval.py 中的 mts_2023 一致
    MACHINE_TYPES_DEV = ["ToyCar", "ToyTrain", "bearing", "fan", "gearbox", "slider", "valve"]
    MACHINE_TYPES_ADD = ["bandsaw", "grinder", "shaker", "ToyDrone", "ToyNscale", "ToyTank", "Vacuum"]
    MACHINE_TYPES_ALL = MACHINE_TYPES_DEV + MACHINE_TYPES_ADD

    # 与 eval.py 中 mts_2023 一致
    MTS = {
        "dev": MACHINE_TYPES_DEV,
        "add": MACHINE_TYPES_ADD,
        "eval": MACHINE_TYPES_ADD,  # eval 集的机器类型与 add 一致
        "all": MACHINE_TYPES_ALL,
    }

    def __init__(self, device: str = None):
        """
        初始化检测引擎

        Args:
            device: 计算设备，None 时自动选择
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.model_config = None
        self.checkpoint_path = None

    def load_model(self, checkpoint_path: str, config: DetectionConfig) -> bool:
        """
        加载模型 - 严格参照 eval.py 的加载逻辑

        Args:
            checkpoint_path: 模型检查点路径
            config: 检测配置

        Returns:
            是否加载成功
        """
        try:
            # 解析检查点路径 - 与 eval.py 一致：支持目录和文件路径
            if os.path.isdir(checkpoint_path):
                candidate = os.path.join(checkpoint_path, "best_model.pth")
                if os.path.exists(candidate):
                    ckpt_file = candidate
                else:
                    raise FileNotFoundError(f"No 'best_model.pth' found in directory: {checkpoint_path}")
            elif os.path.isfile(checkpoint_path):
                ckpt_file = checkpoint_path
            else:
                raise FileNotFoundError(f"Checkpoint path not found: {checkpoint_path}")

            # 保存当前工作目录
            original_cwd = os.getcwd()

            # 切换到 asd_beats 目录，因为 Model_Finetune_BEATs.load_checkpoint()
            # 使用相对路径 ./BEATs_model/BEATs_iter3.pt 加载预训练权重
            os.chdir(str(ASD_BEATS_PATH))

            # 创建参数对象
            args = self._create_args(config)

            # 加载模型 - 与 eval.py 一致
            self.model = Model_Finetune_BEATs(args)
            self.model = self.model.to(self.device)

            # 恢复原工作目录
            os.chdir(original_cwd)

            # 加载权重 - 与 eval.py 一致
            state = torch.load(ckpt_file, map_location=self.device, weights_only=False)
            self.model.load_state_dict(state)
            self.model.eval()

            self.model_config = config
            self.checkpoint_path = ckpt_file

            # ckpt_path 必须是目录 - cal_mean_std 中 os.path.join(ckpt_path, "stat.pth") 需要
            # 如果 ckpt_path 是文件路径，取其所在目录；如果为空，取模型文件所在目录
            if config.ckpt_path and os.path.isfile(config.ckpt_path):
                config.ckpt_path = os.path.dirname(config.ckpt_path)
            elif not config.ckpt_path:
                config.ckpt_path = os.path.dirname(ckpt_file)

            return True

        except Exception as e:
            # 确保恢复工作目录
            if 'original_cwd' in locals():
                os.chdir(original_cwd)
            print(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_args(self, config: DetectionConfig):
        """创建参数对象 - 与 run_eval.sh 和 configs.py 中的参数对应"""
        args = _Args()
        # 模型参数 - 与 run_eval.sh 一致
        args.embedding_dim = config.embedding_dim
        args.pooling_method = config.pooling_method
        args.query = config.query
        args.WAP = config.use_wap
        args.WAP_method = config.wap_method
        args.mel_bins = config.mel_bins
        args.seq_len = int(config.crop_time * 16000 / config.hop_size)
        args.num_classes = config.num_classes
        args.scaler = 15.0
        args.loss_func = "ArcFace"

        # 特征提取参数 - 与 run_eval.sh 一致: --feat_type inv_mel
        args.feat_type = "inv_mel"
        args.norm_method = config.norm_method
        args.hop_size = config.hop_size
        args.window_size = 1024

        # 数据增强参数 (eval模式不启用)
        args.wav_aug = False
        args.spec_aug_f = 0
        args.spec_aug_t = 0

        # 数据路径 - 指向 asd_beats/data 目录
        args.data_path = str(ASD_BEATS_PATH / "data")

        # 数据集参数
        args.crop_time = config.crop_time
        args.num_crops = config.num_crops
        args.batch_size = config.batch_size
        args.num_workers = 0  # Windows 兼容性

        return args

    def run_detection(
        self,
        test_data_path: str,
        train_data_path: str,
        progress_callback=None
    ) -> DetectionResult:
        """
        执行异常检测 - 严格参照 eval.py 的 evaluate() 函数逻辑

        Args:
            test_data_path: 测试数据路径 (eval.npy)
            train_data_path: 训练数据路径 (用于提取 reference embeddings, add.npy)
            progress_callback: 进度回调函数

        Returns:
            检测结果
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        result = DetectionResult()

        # 判断数据集版本 - 与 eval.py 一致
        is_2020 = "2020" in test_data_path
        mts = self.MTS

        # 确定训练/测试数据集名称 - 与 eval.py/run_eval.sh 一致
        # run_eval.sh: --train_dataset All --test_dataset Eval
        train_dataset = self._guess_dataset_name(train_data_path)
        test_dataset = self._guess_dataset_name(test_data_path)

        # 选择机器类型 - 与 eval.py 中 get_dataset_test 逻辑一致
        if test_dataset == "Eval":
            mt_train = mts["add"]  # eval 模式下 reference 用 add.npy
            mt_test = mts["eval"]
        elif test_dataset == "Dev":
            mt_train = mts["dev"]
            mt_test = mts["dev"]
        else:
            mt_train = mts["add"]
            mt_test = mts["add"]

        # ========== Step 1: 计算 mean_std ==========
        # 与 eval.py 中 get_dataset_mean_std + cal_mean_std 一致
        if progress_callback:
            progress_callback(0.05, "Computing mean/std for normalization...")

        args = self._create_args(self.model_config)
        args.train_dataset = train_dataset

        mean_std_loader, machine_type_list = get_dataset_mean_std(train_dataset, mts, args)

        # get_dataset_mean_std() 内部硬编码了 num_workers=6，在 Windows 上会导致 pickle 错误
        # 因此这里用 num_workers=0 重新创建 DataLoader
        mean_std_loader = torch.utils.data.DataLoader(
            mean_std_loader.dataset, batch_size=mean_std_loader.batch_size,
            shuffle=False, num_workers=0, pin_memory=True
        )

        mean_std = cal_mean_std(mean_std_loader, args.norm_method, machine_type_list, self.model_config.ckpt_path, ".")

        # ========== Step 2: 创建数据加载器 ==========
        # 与 eval.py 中 get_dataset_test 一致
        crop_size = int(args.crop_time * 16000 / args.hop_size)
        assert crop_size % 16 == 0, f"Crop size ({crop_size}) must be multiple of 16."
        crop_size = crop_size * args.hop_size

        if progress_callback:
            progress_callback(0.1, "Creating data loaders...")

        # 与 eval.py get_dataset_test 一致: train_ebd 用 add.npy, test 用 eval.npy
        transform_train_ebd = LAMTrainTransform(
            crop_size, args.num_crops, mean_std, "eval", True, "cpu", mt_train, args
        )
        transform_test = LAMTrainTransform(
            crop_size, args.num_crops, mean_std, "eval", True, "cpu", mt_test, args
        )

        dataset_ebd = MyDataset_wav_npy(train_data_path, transform_train_ebd)
        dataset_test = MyDataset_wav_npy(test_data_path, transform_test)

        loader_ebd = torch.utils.data.DataLoader(
            dataset_ebd, batch_size=args.batch_size, shuffle=False, num_workers=0, pin_memory=True
        )
        loader_test = torch.utils.data.DataLoader(
            dataset_test, batch_size=args.batch_size, shuffle=False, num_workers=0, pin_memory=True
        )

        # ========== Step 3: 提取训练集 embeddings ==========
        # 与 eval.py 中 get_embeddings 一致
        if progress_callback:
            progress_callback(0.15, "Extracting training embeddings...")

        with torch.no_grad():
            train_ebds = get_embeddings(self.model, loader_ebd, self.device)

        # ========== Step 4: 推理并计算分数 ==========
        # 与 eval.py 中 evaluate 的推理循环一致
        if progress_callback:
            progress_callback(0.3, "Running inference...")

        score_info = []

        with torch.no_grad():
            total_batches = len(loader_test)
            for i, (data, *labels) in enumerate(loader_test):
                status, sections, machine_ids, machine_types, domains, indexes, filenames = (
                    labels[0], labels[2], labels[3], labels[4], labels[5], labels[6], labels[7]
                )

                n_crops = data.shape[1]
                data = rearrange(data, "b n f t -> (b n) 1 f t")
                data = data.to(self.device, non_blocking=True).float()

                outputs = self.model(data)
                # 与 eval.py 一致: 使用 utils.compute_scores
                scores = compute_scores(outputs, train_ebds, machine_ids.unsqueeze(1).expand(-1, n_crops).reshape(-1))

                scores = rearrange(scores, "(b n) k -> b n k", n=n_crops)

                for index, section, machine_type, domain, score, label, filename in zip(
                    indexes.numpy(),
                    sections.numpy(),
                    machine_types.numpy(),
                    domains,
                    scores.cpu().numpy(),
                    status.numpy(),
                    filenames,
                ):
                    score_info.append([index, section, machine_type, domain, score, label, filename])

                if progress_callback:
                    progress = 0.3 + 0.5 * (i + 1) / total_batches
                    progress_callback(progress, f"Inference: {i+1}/{total_batches}")

        # ========== Step 5: 分数归一化 ==========
        # 与 eval.py 中 score_norm 一致
        if progress_callback:
            progress_callback(0.8, "Normalizing scores...")

        score_info = score_norm(score_info)

        # ========== Step 6: 计算指标 ==========
        # 与 eval.py 中 cal_metrics 一致
        if progress_callback:
            progress_callback(0.9, "Calculating metrics...")

        eval_outputs = cal_metrics(score_info, logpath=".", dataset=test_dataset)

        # 构建结果 - 与 eval.py 输出格式一致
        result.overall = float(eval_outputs["Overall"])
        result.auc_source = float(eval_outputs["auc_source"])
        result.auc_target = float(eval_outputs["auc_target"])
        result.p_auc = float(eval_outputs["p_auc"])

        # 构建每个机器类型的指标
        metrics_type = eval_outputs.get("hmean_types", {})
        auc_source_types = eval_outputs.get("auc_source_types", {})
        auc_target_types = eval_outputs.get("auc_target_types", {})
        pauc_types = eval_outputs.get("pauc_types", {})
        machine_type_list = mt_test
        result.metrics_by_type = {}
        for i, metric_val in metrics_type.items():
            machine_name = machine_type_list[i] if i < len(machine_type_list) else f"type_{i}"
            result.metrics_by_type[machine_name] = {
                "hmean": float(metric_val),
                "auc": float(auc_source_types.get(i, 0.0)),
                "pauc": float(pauc_types.get(i, 0.0)),
            }

        # 转换 sample_scores 为字典格式以供前端使用
        result.sample_scores = []
        for item in score_info:
            index, section, machine_type, domain, score, label, filename = item
            machine_name = machine_type_list[machine_type] if machine_type < len(machine_type_list) else f"type_{machine_type}"
            result.sample_scores.append({
                "index": int(index),
                "section": int(section),
                "machine_type": int(machine_type),
                "machine_name": machine_name,
                "domain": domain,
                "score": float(score),
                "label": int(label),
                "filename": filename
            })

        if progress_callback:
            progress_callback(1.0, "Done!")

        return result

    def _guess_dataset_name(self, data_path: str) -> str:
        """
        从数据文件路径猜测数据集名称
        与 eval.py 中 --train_dataset / --test_dataset 参数对应
        """
        path_lower = data_path.lower()
        if "eval" in path_lower:
            return "Eval"
        elif "dev_test" in path_lower:
            return "Dev"
        elif "add" in path_lower:
            return "Add"
        elif "all" in path_lower:
            return "All"
        elif "dev_train" in path_lower:
            return "Dev"
        else:
            # 默认使用 Eval
            return "Eval"
