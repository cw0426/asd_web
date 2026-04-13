<template>
  <div class="models-page">
    <div class="page-header">
      <h1>模型管理</h1>
      <p>上传和管理训练好的异常检测模型</p>
    </div>

    <!-- 上传区域 -->
    <div class="card-container">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0;">上传新模型</h3>
        <el-button type="primary" @click="showUploadForm = true" v-if="!showUploadForm">
          <el-icon><Plus /></el-icon>
          上传模型
        </el-button>
      </div>

      <!-- 上传表单 -->
      <el-form v-if="showUploadForm" :model="uploadForm" label-width="120px" style="max-width: 600px;">
        <el-form-item label="模型文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            accept=".pth,.pt"
          >
            <template #trigger>
              <el-button type="primary">选择文件</el-button>
            </template>
            <template #tip>
              <div class="el-upload__tip">支持 .pth, .pt 格式，最大 1.5GB</div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="模型名称" required>
          <el-input v-model="uploadForm.name" placeholder="请输入模型名称" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" placeholder="模型描述信息" />
        </el-form-item>

        <el-collapse>
          <el-collapse-item title="高级配置" name="advanced">
            <el-form-item label="池化方法">
              <el-select v-model="uploadForm.pooling_method">
                <el-option label="FMQAP" value="FMQAP" />
                <el-option label="MSFMQAP" value="MSFMQAP" />
                <el-option label="Mean" value="mean" />
              </el-select>
            </el-form-item>

            <el-form-item label="Query 数量">
              <el-input-number v-model="uploadForm.query" :min="1" :max="64" />
            </el-form-item>

            <el-form-item label="嵌入维度">
              <el-input-number v-model="uploadForm.embedding_dim" :min="128" :max="1024" :step="128" />
            </el-form-item>

            <el-form-item label="使用 WAP">
              <el-switch v-model="uploadForm.use_wap" />
            </el-form-item>

            <el-form-item label="类别数">
              <el-input-number v-model="uploadForm.num_classes" :min="1" :max="500" />
            </el-form-item>

            <el-form-item label="训练集">
              <el-select v-model="uploadForm.train_dataset">
                <el-option label="Dev" value="Dev" />
                <el-option label="Add" value="Add" />
                <el-option label="All" value="All" />
              </el-select>
            </el-form-item>

            <el-form-item label="损失函数">
              <el-select v-model="uploadForm.loss_func">
                <el-option label="ArcFace" value="ArcFace" />
                <el-option label="CE" value="CE" />
                <el-option label="AMSoftmax" value="AMSoftmax" />
              </el-select>
            </el-form-item>
          </el-collapse-item>
        </el-collapse>

        <el-form-item>
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            上传
          </el-button>
          <el-button @click="resetUploadForm" :disabled="uploading">取消</el-button>
        </el-form-item>

        <!-- 上传进度条 -->
        <el-form-item v-if="uploading">
          <el-progress :percentage="uploadProgress" :stroke-width="20" :text-inside="true" status="success" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 模型列表 -->
    <div class="card-container">
      <h3 style="margin-bottom: 16px;">模型列表</h3>
      <el-table :data="models" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="模型名称" min-width="150" />
        <el-table-column prop="pooling_method" label="池化方法" width="120" />
        <el-table-column prop="query" label="Query" width="80" />
        <el-table-column prop="train_dataset" label="训练集" width="100" />
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; flex-wrap: nowrap; gap: 8px;">
              <el-button text type="primary" @click="viewModel(row)">
                <el-icon><View /></el-icon>
                详情
              </el-button>
              <el-button text type="primary" @click="validateModel(row)">
                <el-icon><CircleCheck /></el-icon>
                验证
              </el-button>
              <el-button text type="danger" @click="deleteModel(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 模型详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="模型详情" width="600px">
      <el-descriptions :column="2" border v-if="currentModel">
        <el-descriptions-item label="ID">{{ currentModel.id }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ currentModel.name }}</el-descriptions-item>
        <el-descriptions-item label="池化方法">{{ currentModel.pooling_method }}</el-descriptions-item>
        <el-descriptions-item label="Query 数量">{{ currentModel.query }}</el-descriptions-item>
        <el-descriptions-item label="嵌入维度">{{ currentModel.embedding_dim }}</el-descriptions-item>
        <el-descriptions-item label="类别数">{{ currentModel.num_classes }}</el-descriptions-item>
        <el-descriptions-item label="使用 WAP">{{ currentModel.use_wap ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="WAP 方法">{{ currentModel.wap_method }}</el-descriptions-item>
        <el-descriptions-item label="训练集">{{ currentModel.train_dataset }}</el-descriptions-item>
        <el-descriptions-item label="损失函数">{{ currentModel.loss_func }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatSize(currentModel.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ formatTime(currentModel.create_time) }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ currentModel.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi } from '@/api'

const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const models = ref([])
const showUploadForm = ref(false)
const showDetailDialog = ref(false)
const currentModel = ref(null)
const uploadRef = ref(null)
const selectedFile = ref(null)

const uploadForm = ref({
  name: '',
  description: '',
  pooling_method: 'FMQAP',
  query: 24,
  embedding_dim: 768,
  use_wap: false,
  wap_method: 'weighted',
  num_classes: 167,
  train_dataset: 'All',
  train_epochs: 0,
  loss_func: 'ArcFace'
})

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

const formatTime = (time) => {
  if (!time) return '-'
  // 后端返回的是 UTC 时间，需要转换为北京时间 (UTC+8)
  // 添加 'Z' 后缀让 JavaScript 知道这是 UTC 时间
  const utcTime = time.endsWith('Z') ? time : time + 'Z'
  const date = new Date(utcTime)
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择模型文件')
    return
  }
  if (!uploadForm.value.name) {
    ElMessage.warning('请输入模型名称')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('name', uploadForm.value.name)
    formData.append('description', uploadForm.value.description)
    formData.append('pooling_method', uploadForm.value.pooling_method)
    formData.append('query', uploadForm.value.query)
    formData.append('embedding_dim', uploadForm.value.embedding_dim)
    formData.append('use_wap', uploadForm.value.use_wap)
    formData.append('wap_method', uploadForm.value.wap_method)
    formData.append('num_classes', uploadForm.value.num_classes)
    formData.append('train_dataset', uploadForm.value.train_dataset)
    formData.append('train_epochs', uploadForm.value.train_epochs)
    formData.append('loss_func', uploadForm.value.loss_func)

    await modelApi.upload(formData, (progress) => {
      uploadProgress.value = progress
    })

    ElMessage.success('模型上传成功')
    resetUploadForm()
    loadModels()
  } catch (error) {
    console.error('Upload failed:', error)
  } finally {
    uploading.value = false
  }
}

const resetUploadForm = () => {
  showUploadForm.value = false
  selectedFile.value = null
  uploadForm.value = {
    name: '',
    description: '',
    pooling_method: 'FMQAP',
    query: 24,
    embedding_dim: 768,
    use_wap: false,
    wap_method: 'weighted',
    num_classes: 167,
    train_dataset: 'All',
    train_epochs: 0,
    loss_func: 'ArcFace'
  }
}

const viewModel = (model) => {
  currentModel.value = model
  showDetailDialog.value = true
}

const validateModel = async (model) => {
  try {
    const result = await modelApi.validate(model.id)
    if (result.valid) {
      ElMessage.success('模型验证通过')
    } else {
      ElMessage.error('模型验证失败: ' + result.message)
    }
  } catch (error) {
    console.error('Validate failed:', error)
  }
}

const deleteModel = async (model) => {
  try {
    await ElMessageBox.confirm('确定要删除该模型吗？此操作不可恢复。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await modelApi.delete(model.id)
    ElMessage.success('模型已删除')
    loadModels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
    }
  }
}

const loadModels = async () => {
  loading.value = true
  try {
    const result = await modelApi.getList()
    models.value = result.items
  } catch (error) {
    console.error('Load models failed:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadModels()
})
</script>

<style lang="scss" scoped>
.models-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
