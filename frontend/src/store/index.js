import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi, modelApi, taskApi } from '@/api'

export const useAppStore = defineStore('app', () => {
  // 系统信息
  const systemInfo = ref({})
  const modelCount = ref(0)
  const taskCount = ref(0)

  // 加载系统信息
  const loadSystemInfo = async () => {
    try {
      systemInfo.value = await systemApi.getInfo()
    } catch (error) {
      console.error('Load system info failed:', error)
    }
  }

  // 加载统计数据
  const loadStats = async () => {
    try {
      const [models, tasks] = await Promise.all([
        modelApi.getList(0, 1),
        taskApi.getList(null, 0, 1)
      ])
      modelCount.value = models.total
      taskCount.value = tasks.total
    } catch (error) {
      console.error('Load stats failed:', error)
    }
  }

  return {
    systemInfo,
    modelCount,
    taskCount,
    loadSystemInfo,
    loadStats
  }
})
