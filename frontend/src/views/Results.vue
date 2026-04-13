<template>
  <div class="results-page">
    <div class="page-header">
      <h1>检测历史</h1>
      <p>查看历史检测任务和评估结果</p>
    </div>

    <!-- 筛选条件 -->
    <div class="card-container">
      <el-form :inline="true">
        <el-form-item label="任务状态">
          <el-select v-model="filterStatus" clearable placeholder="全部状态" @change="loadTasks">
            <el-option label="等待中" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTasks">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 任务列表 -->
    <div class="card-container">
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="任务ID" width="280">
          <template #default="{ row }">
            <el-link type="primary" @click="viewResult(row)">{{ row.id.substring(0, 8) }}...</el-link>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.progress * 100)"
              :status="getProgressStatus(row.status)"
            />
          </template>
        </el-table-column>

        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>

        <el-table-column prop="end_time" label="完成时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.end_time) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; flex-wrap: nowrap; gap: 8px;">
              <el-button
                text
                type="primary"
                @click="viewResult(row)"
                :disabled="row.status !== 'completed'"
              >
                <el-icon><View /></el-icon>
                查看结果
              </el-button>
              <el-popconfirm
                title="确定要删除该检测记录吗？"
                confirm-button-text="确定"
                cancel-button-text="取消"
                @confirm="deleteTask(row)"
              >
                <template #reference>
                  <el-button
                    text
                    type="danger"
                    :disabled="row.status === 'running'"
                  >
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="margin-top: 20px; text-align: right;">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadTasks"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { taskApi } from '@/api'

const router = useRouter()
const loading = ref(false)
const tasks = ref([])
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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

const viewResult = (task) => {
  if (task.result_id) {
    router.push(`/results/${task.result_id}`)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const result = await taskApi.getList(
      filterStatus.value || null,
      (currentPage.value - 1) * pageSize.value,
      pageSize.value
    )
    tasks.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('Load tasks failed:', error)
  } finally {
    loading.value = false
  }
}

const deleteTask = async (task) => {
  try {
    await taskApi.delete(task.id)
    ElMessage.success('删除成功')
    loadTasks()
  } catch (error) {
    ElMessage.error('删除失败')
    console.error('Delete task failed:', error)
  }
}

onMounted(() => {
  loadTasks()
})
</script>

<style lang="scss" scoped>
.results-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
