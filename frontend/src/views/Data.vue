<template>
  <div class="data-page">
    <div class="page-header">
      <h1>数据管理</h1>
      <p>上传和管理异常检测测试数据文件</p>
    </div>

    <!-- 上传区域 -->
    <div class="card-container">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0;">上传数据文件</h3>
        <el-button type="primary" @click="showUploadForm = true" v-if="!showUploadForm">
          <el-icon><Plus /></el-icon>
          上传数据
        </el-button>
      </div>

      <!-- 上传表单 -->
      <div v-if="showUploadForm">
        <el-alert
          title="数据格式要求"
          type="info"
          style="margin-bottom: 16px;"
          :closable="false"
        >
          <p>支持 .npy 格式的特征文件，文件应包含 "data" 和 "labels" 字段，最大 1.5GB</p>
        </el-alert>

        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          accept=".npy"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">支持 .npy 格式，最大 1.5GB</div>
          </template>
        </el-upload>

        <div style="margin-top: 16px; max-width: 400px;">
          <el-input v-model="uploadDescription" placeholder="数据描述（可选）" style="margin-bottom: 12px;" />
        </div>

        <div style="margin-top: 12px;">
          <el-button type="primary" @click="handleUpload" :loading="uploading">
            上传
          </el-button>
          <el-button @click="resetUploadForm" :disabled="uploading">取消</el-button>
        </div>

        <!-- 上传进度条 -->
        <div v-if="uploading" style="margin-top: 16px; max-width: 500px;">
          <el-progress :percentage="uploadProgress" :stroke-width="20" :text-inside="true" status="success" />
        </div>
      </div>
    </div>

    <!-- 数据文件列表 -->
    <div class="card-container">
      <h3 style="margin-bottom: 16px;">数据文件列表</h3>
      <el-table :data="dataFiles" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column prop="num_samples" label="样本数" width="100" />
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150">
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" @click="deleteDataFile(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { taskApi } from '@/api'

const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const dataFiles = ref([])
const showUploadForm = ref(false)
const uploadRef = ref(null)
const selectedFile = ref(null)
const uploadDescription = ref('')

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
    ElMessage.warning('请选择数据文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('description', uploadDescription.value)

    await taskApi.uploadData(formData, (progress) => {
      uploadProgress.value = progress
    })

    ElMessage.success('数据上传成功')
    resetUploadForm()
    loadDataFiles()
  } catch (error) {
    console.error('Upload failed:', error)
  } finally {
    uploading.value = false
  }
}

const resetUploadForm = () => {
  showUploadForm.value = false
  selectedFile.value = null
  uploadDescription.value = ''
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const deleteDataFile = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该数据文件吗？此操作不可恢复。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await taskApi.deleteDataFile(row.id)
    ElMessage.success('数据文件已删除')
    loadDataFiles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
    }
  }
}

const loadDataFiles = async () => {
  loading.value = true
  try {
    const result = await taskApi.getDataFiles()
    dataFiles.value = result.items
  } catch (error) {
    console.error('Load data files failed:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDataFiles()
})
</script>

<style lang="scss" scoped>
.data-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
