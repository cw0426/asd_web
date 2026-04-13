<template>
  <div class="detection-page">
    <div class="page-header">
      <h1>异常检测</h1>
      <p>选择模型和数据，配置参数并执行异常检测任务</p>
    </div>

    <!-- 步骤指引 -->
    <el-steps :active="currentStep" align-center style="margin-bottom: 30px;">
      <el-step title="选择模型" />
      <el-step title="选择数据" />
      <el-step title="配置与执行" />
    </el-steps>

    <!-- Step 1: 选择模型（玻璃拟态风格） -->
    <div class="card-container" v-show="currentStep === 0">
      <h3 style="margin-bottom: 16px;">
        <span style="color: #FF6B6B; margin-right: 8px;">&#9881;</span>选择检测模型
      </h3>
      <ThreeCarouselSelector
        :models="models"
        :loading="loadingModels"
        @select="handleModelSelect"
      />

      <div style="margin-top: 20px; text-align: right;">
        <el-button type="primary" :disabled="!selectedModel" @click="currentStep = 1">
          下一步
        </el-button>
      </div>
    </div>

    <!-- Step 2: 选择数据 -->
    <div class="card-container" v-show="currentStep === 1">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0;">选择测试数据</h3>
        <router-link to="/data">
          <el-button type="primary" text>
            <el-icon><Plus /></el-icon>
            去上传数据
          </el-button>
        </router-link>
      </div>

      <el-empty v-if="dataFiles.length === 0 && !loadingDataFiles" description="暂无数据文件，请先上传">
        <router-link to="/data">
          <el-button type="primary">前往数据管理上传</el-button>
        </router-link>
      </el-empty>

      <el-table
        v-else
        :data="dataFiles"
        v-loading="loadingDataFiles"
        highlight-current-row
        @current-change="handleDataFileSelect"
        style="width: 100%"
      >
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column prop="num_samples" label="样本数" width="100" />
        <el-table-column prop="file_size" label="大小" width="120">
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
      </el-table>

      <!-- 已选择的数据信息 -->
      <div v-if="selectedDataFile" style="margin-top: 16px; padding: 16px; background: #f0f9eb; border-radius: 8px;">
        <p><strong>已选择:</strong> {{ selectedDataFile.name }}</p>
        <p><strong>样本数量:</strong> {{ selectedDataFile.num_samples }}</p>
        <p><strong>文件大小:</strong> {{ formatSize(selectedDataFile.file_size) }}</p>
      </div>

      <div style="margin-top: 20px; text-align: right;">
        <el-button @click="currentStep = 0">上一步</el-button>
        <el-button type="primary" :disabled="!selectedDataFile" @click="currentStep = 2">
          下一步
        </el-button>
      </div>
    </div>

    <!-- Step 3: 配置参数与执行 -->
    <div class="card-container" v-show="currentStep === 2 && !currentTask">
      <h3 style="margin-bottom: 16px;">检测参数配置</h3>

      <!-- 已选择的模型和数据摘要 -->
      <el-descriptions :column="2" border style="margin-bottom: 20px;">
        <el-descriptions-item label="模型">{{ selectedModel?.name }}</el-descriptions-item>
        <el-descriptions-item label="数据">{{ selectedDataFile?.name }}</el-descriptions-item>
      </el-descriptions>

      <el-form :model="taskConfig" label-width="140px" style="max-width: 500px;">
        <el-form-item label="裁剪时长(秒)">
          <el-input-number v-model="taskConfig.crop_time" :min="1" :max="10" :step="0.256" :precision="3" />
        </el-form-item>

        <el-form-item label="裁剪数量">
          <el-input-number v-model="taskConfig.num_crops" :min="1" :max="10" />
        </el-form-item>

        <el-form-item label="批量大小">
          <el-input-number v-model="taskConfig.batch_size" :min="1" :max="128" />
        </el-form-item>

        <el-form-item label="归一化方法">
          <el-select v-model="taskConfig.norm_method">
            <el-option label="均值标准差" value="mean_std" />
            <el-option label="最大最小值" value="min_max" />
            <el-option label="无归一化" value="none" />
          </el-select>
        </el-form-item>
      </el-form>

      <div style="margin-top: 20px; text-align: right;">
        <el-button @click="currentStep = 1">上一步</el-button>
        <el-button type="primary" @click="startDetection" :loading="creating">
          开始检测
        </el-button>
      </div>
    </div>

    <!-- 执行检测进度 -->
    <div class="card-container" v-if="currentTask">
      <h3 style="margin-bottom: 16px;">检测任务</h3>

      <div style="text-align: center; padding: 40px;">
        <el-progress
          type="dashboard"
          :percentage="Math.round(currentTask.progress * 100)"
          :status="getProgressStatus(currentTask.status)"
        >
          <template #default="{ percentage }">
            <span class="percentage-value">{{ percentage }}%</span>
          </template>
        </el-progress>

        <p style="margin-top: 20px; font-size: 18px;">
          <el-tag :type="getStatusType(currentTask.status)" size="large">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
        </p>

        <p v-if="currentTask.progress_message" style="margin-top: 10px; color: #606266; font-size: 14px;">
          {{ currentTask.progress_message }}
        </p>

        <p style="margin-top: 10px; color: #909399;">
          任务 ID: {{ currentTask.id }}
        </p>

        <div style="margin-top: 30px;" v-if="currentTask.status === 'completed'">
          <el-button type="success" size="large" @click="viewResult">
            查看结果
          </el-button>
          <el-button size="large" @click="resetDetection">
            新建检测
          </el-button>
        </div>

        <div style="margin-top: 30px;" v-if="currentTask.status === 'failed'">
          <el-alert :title="currentTask.error_message" type="error" show-icon />
          <el-button style="margin-top: 16px;" @click="resetDetection">
            重新配置
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { modelApi, taskApi } from '@/api'
import ThreeCarouselSelector from '@/components/ThreeCarouselSelector.vue'

const router = useRouter()
const currentStep = ref(0)
const loadingModels = ref(false)
const loadingDataFiles = ref(false)
const creating = ref(false)
const models = ref([])
const dataFiles = ref([])
const selectedModel = ref(null)
const selectedDataFile = ref(null)
const currentTask = ref(null)
let pollTimer = null

const taskConfig = ref({
  crop_time: 4.096,
  num_crops: 5,
  batch_size: 50,
  norm_method: 'mean_std'
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

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return null
}

const handleModelSelect = (row) => {
  selectedModel.value = row
}

const handleDataFileSelect = (row) => {
  selectedDataFile.value = row
}

const startDetection = async () => {
  if (!selectedModel.value || !selectedDataFile.value) {
    ElMessage.warning('请选择模型和数据文件')
    return
  }

  creating.value = true
  try {
    const result = await taskApi.create({
      model_id: selectedModel.value.id,
      data_file_id: selectedDataFile.value.id,
      config: taskConfig.value
    })

    currentTask.value = result
    startPolling()
  } catch (error) {
    console.error('Create task failed:', error)
  } finally {
    creating.value = false
  }
}

const resetDetection = () => {
  currentTask.value = null
  currentStep.value = 0
}

const startPolling = () => {
  pollTimer = setInterval(async () => {
    if (!currentTask.value) return

    try {
      const task = await taskApi.getDetail(currentTask.value.id)
      currentTask.value = task

      if (task.status === 'completed' || task.status === 'failed') {
        stopPolling()
      }
    } catch (error) {
      console.error('Poll task failed:', error)
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const viewResult = () => {
  if (currentTask.value && currentTask.value.result_id) {
    router.push(`/results/${currentTask.value.result_id}`)
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const result = await modelApi.getList()
    models.value = result.items
  } catch (error) {
    console.error('Load models failed:', error)
  } finally {
    loadingModels.value = false
  }
}

const loadDataFiles = async () => {
  loadingDataFiles.value = true
  try {
    const result = await taskApi.getDataFiles()
    dataFiles.value = result.items
  } catch (error) {
    console.error('Load data files failed:', error)
  } finally {
    loadingDataFiles.value = false
  }
}

onMounted(() => {
  loadModels()
  loadDataFiles()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.detection-page {
  max-width: 900px;
  margin: 0 auto;
}

.percentage-value {
  font-size: 28px;
  font-weight: bold;
}
</style>
