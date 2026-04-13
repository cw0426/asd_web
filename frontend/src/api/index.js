import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000 // 5分钟超时，适应大文件上传和长时间推理
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// ==================== 模型相关 API ====================

export const modelApi = {
  // 上传模型
  upload(formData, onProgress) {
    return api.post('/models/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    })
  },

  // 获取模型列表
  getList(skip = 0, limit = 100) {
    return api.get('/models', { params: { skip, limit } })
  },

  // 获取模型详情
  getDetail(modelId) {
    return api.get(`/models/${modelId}`)
  },

  // 更新模型
  update(modelId, data) {
    return api.put(`/models/${modelId}`, data)
  },

  // 删除模型
  delete(modelId) {
    return api.delete(`/models/${modelId}`)
  },

  // 验证模型
  validate(modelId) {
    return api.post(`/models/${modelId}/validate`)
  }
}

// ==================== 任务相关 API ====================

export const taskApi = {
  // 上传数据文件
  uploadData(formData, onProgress) {
    return api.post('/tasks/upload-data', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
    })
  },

  // 获取数据文件列表
  getDataFiles(skip = 0, limit = 100) {
    return api.get('/tasks/data-files', { params: { skip, limit } })
  },

  // 获取数据文件详情
  getDataFile(dataFileId) {
    return api.get(`/tasks/data-files/${dataFileId}`)
  },

  // 删除数据文件
  deleteDataFile(dataFileId) {
    return api.delete(`/tasks/data-files/${dataFileId}`)
  },

  // 创建检测任务
  create(data) {
    return api.post('/tasks', data)
  },

  // 获取任务列表
  getList(status = null, skip = 0, limit = 100) {
    return api.get('/tasks', { params: { status, skip, limit } })
  },

  // 获取任务详情
  getDetail(taskId) {
    return api.get(`/tasks/${taskId}`)
  },

  // 取消任务
  cancel(taskId) {
    return api.post(`/tasks/${taskId}/cancel`)
  },

  // 删除任务
  delete(taskId) {
    return api.delete(`/tasks/${taskId}`)
  }
}

// ==================== 结果相关 API ====================

export const resultApi = {
  // 获取检测结果
  getDetail(resultId) {
    return api.get(`/results/${resultId}`)
  },

  // 根据任务ID获取结果
  getByTask(taskId) {
    return api.get(`/results/task/${taskId}`)
  },

  // 获取样本结果
  getSamples(resultId, machineType = null, skip = 0, limit = 100) {
    return api.get(`/results/${resultId}/samples`, {
      params: { machine_type: machineType, skip, limit }
    })
  },

  // 导出结果
  exportResult(resultId, format = 'csv') {
    return api.get(`/results/${resultId}/export`, {
      params: { format },
      responseType: 'blob'
    })
  },

  // 获取分数分布
  getDistribution(resultId, bins = 20) {
    return api.get(`/results/${resultId}/distribution`, {
      params: { bins }
    })
  },

  // 获取 ROC 曲线
  getRocCurve(resultId) {
    return api.get(`/results/${resultId}/roc`)
  }
}

// ==================== 系统 API ====================

export const systemApi = {
  // 获取系统信息
  getInfo() {
    return api.get('/info')
  },

  // 健康检查
  healthCheck() {
    return api.get('/health')
  }
}

export default api
