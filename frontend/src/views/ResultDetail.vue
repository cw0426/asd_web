<template>
  <div class="result-detail-page">
    <div class="page-header">
      <el-button @click="$router.back()" style="margin-bottom: 16px;">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1>检测结果详情</h1>
    </div>

    <div v-loading="loading">
      <!-- 总体指标 -->
      <div class="card-container" v-if="result">
        <h3 style="margin-bottom: 20px;">总体指标</h3>
        <div class="stat-cards">
          <div class="stat-card primary">
            <div class="stat-title">Overall (hmean)</div>
            <div class="stat-value">{{ (result.overall * 100).toFixed(2) }}%</div>
          </div>
          <div class="stat-card success">
            <div class="stat-title">AUC (Source)</div>
            <div class="stat-value">{{ (result.auc_source * 100).toFixed(2) }}%</div>
          </div>
          <div class="stat-card warning">
            <div class="stat-title">AUC (Target)</div>
            <div class="stat-value">{{ (result.auc_target * 100).toFixed(2) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">pAUC</div>
            <div class="stat-value">{{ (result.p_auc * 100).toFixed(2) }}%</div>
          </div>
        </div>
      </div>

      <!-- 分类型指标 -->
      <div class="card-container" v-if="result">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0;">分类型指标</h3>
          <div>
            <el-button type="primary" @click="exportResult('csv')">
              <el-icon><Download /></el-icon>
              导出 CSV
            </el-button>
            <el-button @click="exportResult('json')">
              <el-icon><Download /></el-icon>
              导出 JSON
            </el-button>
          </div>
        </div>

        <el-table :data="metricsTableData" style="width: 100%">
          <el-table-column prop="machine_type" label="机器类型" width="150" />
          <el-table-column prop="auc" label="AUC (Source)" width="150">
            <template #default="{ row }">
              {{ (row.auc * 100).toFixed(2) }}%
            </template>
          </el-table-column>
          <el-table-column prop="pauc" label="pAUC" width="150">
            <template #default="{ row }">
              {{ (row.pauc * 100).toFixed(2) }}%
            </template>
          </el-table-column>
          <el-table-column prop="hmean" label="H-Mean" width="150">
            <template #default="{ row }">
              {{ (row.hmean * 100).toFixed(2) }}%
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 指标可视化图表 -->
      <div class="card-container" v-if="result">
        <h3 style="margin-bottom: 16px;">指标可视化</h3>
        <el-row :gutter="20">
          <el-col :span="12">
            <div ref="barChartRef" style="height: 400px;"></div>
          </el-col>
          <el-col :span="12">
            <div ref="radarChartRef" style="height: 400px;"></div>
          </el-col>
        </el-row>
      </div>

      <!-- 样本详情 -->
      <div class="card-container" v-if="result">
        <h3 style="margin-bottom: 16px;">样本检测结果</h3>
        <el-table :data="samples" v-loading="loadingSamples" style="width: 100%">
          <el-table-column prop="sample_index" label="索引" width="80" />
          <el-table-column prop="machine_type" label="机器类型" width="120">
            <template #default="{ row }">
              {{ row.machine_name || `Type ${row.machine_type}` }}
            </template>
          </el-table-column>
          <el-table-column prop="domain" label="域" width="100" />
          <el-table-column prop="score" label="异常分数" width="150">
            <template #default="{ row }">
              {{ row.score.toFixed(4) }}
            </template>
          </el-table-column>
          <el-table-column prop="label" label="标签" width="100">
            <template #default="{ row }">
              <el-tag :type="row.label === 0 ? 'success' : 'danger'">
                {{ row.label === 0 ? '正常' : '异常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="filename" label="文件名" min-width="200" />
        </el-table>

        <div style="margin-top: 20px; text-align: right;">
          <el-pagination
            v-model:current-page="samplePage"
            :page-size="samplePageSize"
            :total="sampleTotal"
            layout="total, prev, pager, next"
            @current-change="loadSamples"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { resultApi } from '@/api'

const route = useRoute()
const loading = ref(true)
const loadingSamples = ref(false)
const result = ref(null)
const samples = ref([])
const samplePage = ref(1)
const samplePageSize = ref(20)
const sampleTotal = ref(0)
const barChartRef = ref(null)
const radarChartRef = ref(null)
let barChart = null
let radarChart = null

const metricsTableData = computed(() => {
  if (!result.value) return []
  return Object.entries(result.value.metrics_by_type).map(([type, metrics]) => ({
    machine_type: type,
    auc: metrics.auc,
    pauc: metrics.pauc,
    hmean: metrics.hmean
  }))
})

const loadResult = async () => {
  loading.value = true
  try {
    result.value = await resultApi.getDetail(route.params.id)
    await nextTick()
    renderCharts()
  } catch (error) {
    ElMessage.error('加载结果失败')
    console.error('Load result failed:', error)
  } finally {
    loading.value = false
  }
}

const loadSamples = async () => {
  loadingSamples.value = true
  try {
    const res = await resultApi.getSamples(
      route.params.id,
      null,
      (samplePage.value - 1) * samplePageSize.value,
      samplePageSize.value
    )
    samples.value = res.items
    sampleTotal.value = res.total
  } catch (error) {
    console.error('Load samples failed:', error)
  } finally {
    loadingSamples.value = false
  }
}

const exportResult = async (format) => {
  try {
    const response = await resultApi.exportResult(route.params.id, format)
    const blob = new Blob([response], {
      type: format === 'csv' ? 'text/csv' : 'application/json'
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `result_${route.params.id}.${format}`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('导出失败')
    console.error('Export failed:', error)
  }
}

const renderCharts = () => {
  if (!result.value) return

  const types = Object.keys(result.value.metrics_by_type || {})

  // 如果没有分类型指标数据，不渲染图表
  if (types.length === 0) {
    console.warn('No metrics_by_type data available for charts')
    return
  }

  // 柱状图
  if (barChartRef.value) {
    if (barChart) barChart.dispose()
    barChart = echarts.init(barChartRef.value)

    const aucData = types.map(t => parseFloat((result.value.metrics_by_type[t].auc * 100).toFixed(2)))
    const paucData = types.map(t => parseFloat((result.value.metrics_by_type[t].pauc * 100).toFixed(2)))

    barChart.setOption({
      title: { text: '各机器类型指标对比', left: 'center' },
      tooltip: { trigger: 'axis' },
      legend: { data: ['AUC', 'pAUC'], bottom: 0 },
      xAxis: { type: 'category', data: types, axisLabel: { rotate: 45 } },
      yAxis: { type: 'value', name: '百分比 (%)', max: 100 },
      series: [
        { name: 'AUC', type: 'bar', data: aucData },
        { name: 'pAUC', type: 'bar', data: paucData }
      ]
    })
  }

  // 雷达图
  if (radarChartRef.value) {
    if (radarChart) radarChart.dispose()
    radarChart = echarts.init(radarChartRef.value)

    const indicator = types.map(t => ({ name: t, max: 100 }))
    const hmeanData = types.map(t => parseFloat((result.value.metrics_by_type[t].hmean * 100).toFixed(2)))

    radarChart.setOption({
      title: { text: 'H-Mean 雷达图', left: 'center' },
      tooltip: {},
      radar: { indicator },
      series: [{
        type: 'radar',
        data: [{ value: hmeanData, name: 'H-Mean' }]
      }]
    })
  }
}

onMounted(() => {
  loadResult()
  loadSamples()
})

watch(() => route.params.id, () => {
  loadResult()
  loadSamples()
})
</script>

<style lang="scss" scoped>
.result-detail-page {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
