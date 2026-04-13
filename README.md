# asd_web - 异常声音检测系统

基于 BEATs 预训练模型的机器异常声音检测 Web 系统，支持 DCASE 2023 Task 2 数据集。

## 项目简介

asd_web 是一个完整的异常声音检测系统，提供友好的 Web 界面用于：

- 管理训练好的异常检测模型
- 上传和管理测试数据
- 执行异常检测任务
- 分析和导出检测结果

系统采用前后端分离架构，后端基于 FastAPI，前端使用 Vue.js 3 + Element Plus。

## 功能特性

### 核心功能

- **模型管理**：上传、配置、管理训练好的检测模型（支持 .pth/.pt 格式）
- **数据管理**：上传和管理测试数据文件（支持 .npy 格式）
- **异常检测**：执行实时异常检测任务，支持进度追踪
- **结果分析**：可视化展示检测指标，支持 ROC 曲线、分数分布图
- **结果导出**：支持 CSV、JSON 格式导出

### 技术亮点

- 基于 BEATs 预训练模型的音频特征提取
- 支持 DCASE 2023 Task 2 标准评估指标（AUC Source/Target、pAUC）
- 3D 交互式模型选择器
- 异步任务处理与实时进度反馈
- 多种池化方法支持（FMQAP、MSFMQAP、MSDualDimMQAP）

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue.js 3)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │  首页   │ │模型管理 │ │数据管理 │ │异常检测 │ │结果查看 ││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘│
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │模型 API │ │任务 API │ │结果 API │ │系统 API │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └─────────┘           │
│       │          │          │                               │
│  ┌────▼──────────▼──────────▼────┐                         │
│  │         SQLite 数据库          │                         │
│  └───────────────────────────────┘                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   检测引擎 (asd_beats)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ BEATs 模型  │  │  数据处理   │  │  评估工具   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
asd_web/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/                # API 路由
│   │   │   ├── models.py       # 模型管理 API
│   │   │   ├── tasks.py        # 任务管理 API
│   │   │   └── results.py      # 结果查询 API
│   │   ├── core/
│   │   │   └── detector.py     # 异常检测引擎
│   │   ├── db/
│   │   │   ├── database.py     # 数据库配置
│   │   │   └── crud.py         # 数据库操作
│   │   ├── models/
│   │   │   ├── model.py        # ORM 模型
│   │   │   └── schemas.py      # Pydantic 模式
│   │   ├── config.py           # 配置文件
│   │   └── main.py             # 应用入口
│   ├── uploads/                # 上传文件存储
│   ├── results/                # 检测结果存储
│   ├── asd_web.db              # SQLite 数据库
│   └── requirements.txt        # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 公共组件
│   │   ├── api/                # API 接口
│   │   ├── router/             # 路由配置
│   │   ├── store/              # 状态管理
│   │   └── utils/              # 工具函数
│   ├── vite.config.js          # Vite 配置
│   └── package.json            # npm 依赖
│
└── README.md
```

## 技术栈

### 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.8 | 编程语言 |
| FastAPI | 0.109.0 | Web 框架 |
| SQLAlchemy | 2.0.25 | ORM 框架 |
| PyTorch | >= 2.0.0 | 深度学习框架 |
| torchaudio | >= 2.0.0 | 音频处理 |
| NumPy | >= 1.24.0 | 数值计算 |
| scikit-learn | >= 1.2.0 | 机器学习工具 |

### 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue.js | 3.4.0 | 前端框架 |
| Element Plus | 2.4.4 | UI 组件库 |
| ECharts | 5.4.3 | 数据可视化 |
| Three.js | 0.183.2 | 3D 渲染 |
| Axios | 1.6.5 | HTTP 客户端 |
| Vite | 5.0.10 | 构建工具 |

## 快速开始

### 环境要求

- Python >= 3.8
- Node.js >= 16.0
- CUDA 11.x+（如使用 GPU）

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/yourusername/asd_web.git
cd asd_web
```

2. **安装后端依赖**

```bash
cd backend
pip install -r requirements.txt
```

3. **安装前端依赖**

```bash
cd ../frontend
npm install
```

4. **准备 BEATs 预训练模型**

下载 BEATs 预训练模型并放置到 `asd_beats/BEATs_model/BEATs_iter3.pt`

```bash
# 确保以下文件存在
ls ../asd_beats/BEATs_model/BEATs_iter3.pt
```

5. **准备训练数据**

将训练数据文件 `add.npy` 放置到 `asd_beats/data/` 目录：

```bash
# 确保以下文件存在
ls ../asd_beats/data/add.npy
```

### 启动服务

1. **启动后端服务**

```bash
cd backend
python -m app.main
```

后端服务运行在 `http://localhost:8000`

2. **启动前端服务**

```bash
cd frontend
npm run dev
```

前端服务运行在 `http://localhost:3000`

3. **访问系统**

打开浏览器访问 `http://localhost:3000`

## 使用指南

### 1. 上传模型

1. 进入「模型管理」页面
2. 点击「上传模型」按钮
3. 选择训练好的模型文件（.pth 或 .pt 格式）
4. 配置模型参数：
   - **池化方法**：FMQAP、MSFMQAP、MSDualDimMQAP 等
   - **Query 数量**：默认 24
   - **嵌入维度**：默认 768
   - **训练数据集**：Dev、Add、All
   - **损失函数**：ArcFace、CE、AMSoftmax
5. 点击「保存」完成上传

### 2. 上传测试数据

1. 进入「数据管理」页面
2. 点击「上传数据」按钮
3. 选择测试数据文件（.npy 格式）
4. 数据文件需包含 `data` 和 `labels` 字段

### 3. 执行检测

1. 进入「异常检测」页面
2. 选择已上传的模型
3. 选择测试数据文件
4. 配置检测参数：
   - **裁剪时长**：1-10 秒
   - **裁剪数量**：1-10
   - **批量大小**：1-128
   - **归一化方法**：mean_std、min_max、none
5. 点击「开始检测」
6. 实时查看检测进度

### 4. 查看结果

1. 进入「历史记录」页面
2. 选择检测结果查看详情
3. 查看评估指标：
   - **Overall Score**：总体分数（调和平均）
   - **AUC (Source)**：源域 AUC
   - **AUC (Target)**：目标域 AUC
   - **pAUC**：部分 AUC
4. 查看 ROC 曲线和分数分布
5. 导出结果（CSV/JSON）

## 数据格式

### 模型文件

支持 PyTorch 模型文件（.pth 或 .pt），模型需兼容 BEATs 架构。

### 测试数据文件

采用 NumPy 格式（.npy），结构如下：

```python
{
    "data": numpy.ndarray,  # 形状: (N, F, T)，音频特征
    "labels": [
        {
            "machine_status": int,      # 0=正常, 1=异常
            "machine_att": int,         # 属性标签
            "machine_section": int,     # 分区 ID
            "machine_id": int,          # 机器 ID
            "machine_type": int,        # 机器类型 ID
            "machine_domain": str,      # "source" 或 "target"
            "index": int,               # 样本索引
            "filename": str             # 原始文件名
        },
        ...
    ]
}
```

## API 接口

### 模型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/models/upload` | 上传模型 |
| GET | `/api/models` | 获取模型列表 |
| GET | `/api/models/{id}` | 获取模型详情 |
| PUT | `/api/models/{id}` | 更新模型信息 |
| DELETE | `/api/models/{id}` | 删除模型 |

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/upload-data` | 上传测试数据 |
| GET | `/api/tasks/data-files` | 获取数据文件列表 |
| DELETE | `/api/tasks/data-files/{id}` | 删除数据文件 |
| POST | `/api/tasks` | 创建检测任务 |
| GET | `/api/tasks` | 获取任务列表 |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| POST | `/api/tasks/{id}/cancel` | 取消任务 |

### 结果查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/results/{id}` | 获取检测结果 |
| GET | `/api/results/{id}/samples` | 获取样本结果 |
| GET | `/api/results/{id}/export` | 导出结果 |
| GET | `/api/results/{id}/distribution` | 获取分数分布 |
| GET | `/api/results/{id}/roc` | 获取 ROC 数据 |

## 支持的机器类型

### DCASE 2023 Task 2

| ID | 机器类型 |
|----|----------|
| 0 | bandsaw |
| 1 | grinder |
| 2 | shaker |
| 3 | ToyDrone |
| 4 | ToyNscale |
| 5 | ToyTank |
| 6 | Vacuum |

### DCASE 2020/2021 Task 2

| ID | 机器类型 |
|----|----------|
| 0 | ToyCar |
| 1 | ToyTrain |
| 2 | bearing |
| 3 | fan |
| 4 | gearbox |
| 5 | slider |
| 6 | valve |

## 评估指标

系统支持 DCASE 2023 Task 2 标准评估指标：

- **Overall Score**：AUC (source)、AUC (target)、pAUC 的调和平均值
- **AUC (Source)**：源域正常样本 + 所有异常样本计算的 AUC
- **AUC (Target)**：目标域正常样本 + 所有异常样本计算的 AUC
- **pAUC**：FPR <= 0.1 时的部分 AUC

## 配置说明

### 后端配置

编辑 `backend/app/config.py`：

```python
# 数据库路径
DATABASE_URL = "sqlite+aiosqlite:///./asd_web.db"

# 上传文件大小限制
MAX_UPLOAD_SIZE = 1500 * 1024 * 1024  # 1.5GB

# BEATs 预训练模型路径
BEATS_CHECKPOINT = "../asd_beats/BEATs_model/BEATs_iter3.pt"
```

### 前端配置

编辑 `frontend/vite.config.js`：

```javascript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        timeout: 600000
      }
    }
  }
})
```

## 依赖项目

本项目依赖以下核心项目：

- **[asd_beats](../asd_beats)**：核心异常检测算法库
- **[BEATs](https://github.com/microsoft/unilm/tree/master/beats)**：微软音频预训练模型

## 参考文献

- Dohi, K., et al. "Description and Discussion on DCASE 2023 Challenge Task 2: First-Shot Unsupervised Anomalous Sound Detection for Machine Condition Monitoring," arXiv:2305.07828, 2023.
- Chen, S., et al. "BEATs: Audio Pre-Training with Acoustic Tokenizers," arXiv:2212.09058, 2022.

## 许可证

本项目仅供学术研究使用。

## 致谢

- DCASE Challenge Task 2
- Microsoft BEATs Team
