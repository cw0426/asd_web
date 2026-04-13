<template>
  <div class="home-page">
    <div class="page-header">
      <h1>异常音频检测系统</h1>
      <p>基于 BEATs 预训练模型的机器声音异常检测平台</p>
    </div>

    <!-- 系统状态 -->
    <div class="card-container" v-loading="loading">
      <h3 style="margin-bottom: 16px;">系统状态</h3>
      <div class="stat-cards">
        <div class="stat-card primary">
          <div class="stat-title">计算设备</div>
          <div class="stat-value">{{ systemInfo.device || '-' }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-title">已上传模型</div>
          <div class="stat-value">{{ modelCount }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-title">检测任务</div>
          <div class="stat-value">{{ taskCount }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title">PyTorch 版本</div>
          <div class="stat-value" style="font-size: 18px;">{{ systemInfo.pytorch_version || '-' }}</div>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="card-container">
      <h3 style="margin-bottom: 16px;">快速操作</h3>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-button type="primary" size="large" @click="$router.push('/models')">
            <el-icon><Upload /></el-icon>
            上传模型
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button size="large" @click="$router.push('/data')">
            <el-icon><Document /></el-icon>
            数据管理
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button type="success" size="large" @click="$router.push('/detection')">
            <el-icon><Cpu /></el-icon>
            开始检测
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button type="warning" size="large" @click="$router.push('/results')">
            <el-icon><DataAnalysis /></el-icon>
            查看结果
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 使用流程 -->
    <div class="card-container">
      <h3 style="margin-bottom: 20px;">使用流程</h3>
      <el-steps :active="0" align-center>
        <el-step title="上传模型" description="上传训练好的 checkpoint 文件" />
        <el-step title="上传数据" description="上传测试数据文件 (eval.npy)" />
        <el-step title="执行检测" description="选择模型和数据进行检测" />
        <el-step title="查看结果" description="分析评估指标和详细结果" />
      </el-steps>
    </div>

    <!-- 最近任务 -->
    <div class="card-container">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0;">最近任务</h3>
        <el-button text type="primary" @click="$router.push('/results')">
          查看全部
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      <el-table :data="recentTasks" style="width: 100%">
        <el-table-column prop="id" label="任务ID" width="280">
          <template #default="{ row }">
            <el-link type="primary" @click="viewTaskResult(row)">{{ row.id.substring(0, 8) }}...</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(row.progress * 100)" :status="getProgressStatus(row.status)" />
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { systemApi, modelApi, taskApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const systemInfo = ref({})
const modelCount = ref(0)
const taskCount = ref(0)
const recentTasks = ref([])

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

const viewTaskResult = (task) => {
  if (task.status === 'completed' && task.result_id) {
    router.push(`/results/${task.result_id}`)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    // 并行请求
    const [info, models, tasks] = await Promise.all([
      systemApi.getInfo(),
      modelApi.getList(),
      taskApi.getList(null, 0, 5)
    ])

    systemInfo.value = info
    modelCount.value = models.total
    taskCount.value = tasks.total
    recentTasks.value = tasks.items
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
