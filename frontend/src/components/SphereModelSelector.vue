<template>
  <div class="sphere-selector" ref="containerRef">
    <!-- 粒子 Canvas 层 -->
    <canvas ref="particleCanvas" class="particle-layer" />

    <!-- 3D 球体容器 -->
    <div class="sphere-container" ref="sphereRef">
      <!-- 球体上的模型卡片 -->
      <div
        v-for="(model, index) in models"
        :key="model.id"
        class="sphere-card"
        :class="{
          active: index === activeIndex,
          locked: isLocked && index === activeIndex
        }"
        :ref="el => setCardRef(el, index)"
        @click="selectCard(index)"
      >
        <div class="card-glow" />
        <div class="card-scanline" />
        <div class="card-content">
          <div class="card-header">
            <span class="card-icon">&#9881;</span>
            <span class="card-name">{{ model.name }}</span>
          </div>
          <div class="card-divider" />
          <div class="card-info" v-if="index === activeIndex">
            <div class="info-row">
              <span class="info-label">池化方法</span>
              <span class="info-value">{{ model.pooling_method }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">训练集</span>
              <span class="info-value">{{ model.train_dataset }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">类别数</span>
              <span class="info-value">{{ model.num_classes }}</span>
            </div>
          </div>
        </div>
        <div class="card-shadow" />
      </div>

      <!-- 中心光晕 -->
      <div class="center-glow" />
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-if="models.length === 0 && !loading">
      <div class="empty-icon">&#9881;</div>
      <p>暂无模型</p>
      <p class="empty-hint">请先在模型管理页面上传模型</p>
    </div>

    <!-- 加载中 -->
    <div class="loading-state" v-if="loading">
      <div class="loading-ring" />
      <p>加载模型数据...</p>
    </div>

    <!-- 底部控制栏 -->
    <div class="control-bar">
      <!-- 当前模型指示 -->
      <div class="current-indicator" v-if="currentModel">
        <span class="indicator-label">当前选择:</span>
        <span class="indicator-value">{{ currentModel.name }}</span>
      </div>

      <!-- 手势控制区 -->
      <div class="gesture-section">
        <el-switch
          v-model="gestureMode"
          active-text="手势模式"
          inactive-text=""
          @change="onGestureModeChange"
        />

        <!-- 摄像头预览 -->
        <div class="camera-preview" v-show="gestureMode">
          <video ref="videoEl" autoplay playsinline muted />
          <canvas ref="handCanvas" class="hand-overlay" />
          <div class="camera-border" />
        </div>

        <!-- 手势状态 -->
        <div class="gesture-status" v-show="gestureMode">
          <span class="status-dot" :class="gestureState" />
          <span class="status-text">{{ gestureStatusText }}</span>
        </div>
      </div>

      <!-- 确认按钮 -->
      <el-button
        type="primary"
        class="confirm-btn"
        :disabled="!currentModel || isLocked"
        @click="confirmSelect"
      >
        <span v-if="!isLocked">&#10003; 确认选择</span>
        <span v-else class="locked-text">&#128274; 已锁定</span>
      </el-button>
    </div>

    <!-- 手势操作提示 -->
    <div class="gesture-hints" v-show="gestureMode">
      <div class="hint-item">
        <span class="hint-icon">&#128076;</span>
        啄木鸟手势旋转球体
      </div>
      <div class="hint-item">
        <span class="hint-icon">&#9995;</span>
        张开手掌停止旋转
      </div>
      <div class="hint-item">
        <span class="hint-icon">&#9994;</span>
        握拳锁定模型
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { SphereParticleEngine } from '@/utils/sphereParticleEngine'
import { GestureDetector } from '@/utils/gestureDetector'

const props = defineProps({
  models: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

// Refs
const containerRef = ref(null)
const sphereRef = ref(null)
const particleCanvas = ref(null)
const videoEl = ref(null)
const handCanvas = ref(null)

// 卡片 DOM 元素引用
const cardRefs = {}
const setCardRef = (el, index) => {
  if (el) cardRefs[index] = el
}

// 状态
const activeIndex = ref(0)
const isLocked = ref(false)
const gestureMode = ref(false)
const gestureState = ref('idle')

// 3D 球体参数
let sphereRadius = 280
let rotationX = 0
let rotationY = 0
let targetRotationX = 0
let targetRotationY = 0
let autoRotateSpeed = 0.005
let isAutoRotating = true

// 粒子引擎 & 手势检测
let particleEngine = null
let gestureDetector = null
let animationFrameId = null

// 计算属性
const currentModel = computed(() => props.models[activeIndex.value])

const gestureStatusText = computed(() => {
  const map = {
    idle: '等待手势...',
    open: '手掌张开 - 停止旋转',
    fist: '握拳 - 锁定模型',
    woodpecker: '啄木鸟 - 旋转球体',
    swipe_left: '左滑',
    swipe_right: '右滑'
  }
  return map[gestureState.value] || '等待手势...'
})

// 计算单个卡片的位置样式
const getCardStyle = (index, total) => {
  // 使用斐波那契球面分布算法
  const phi = Math.acos(1 - 2 * (index + 0.5) / total)
  const theta = Math.PI * (1 + Math.sqrt(5)) * (index + 0.5)

  const radius = sphereRadius

  // 应用旋转
  const rotatedPhi = phi + rotationX
  const rotatedTheta = theta + rotationY

  // 3D 坐标
  const x = radius * Math.sin(rotatedPhi) * Math.cos(rotatedTheta)
  const y = radius * Math.cos(rotatedPhi)
  const z = radius * Math.sin(rotatedPhi) * Math.sin(rotatedTheta)

  // 计算可见性和缩放
  const scale = 0.5 + (z + radius) / (2 * radius) * 0.5
  const opacity = 0.3 + (z + radius) / (2 * radius) * 0.7

  // 计算旋转角度
  const rotateY = -rotatedTheta * (180 / Math.PI)
  const rotateX = -rotatedPhi * (180 / Math.PI) + 90

  return {
    transform: `translate3d(${x}px, ${y}px, ${z}px) rotateY(${rotateY}deg) rotateX(${rotateX}deg) scale(${scale})`,
    opacity: opacity,
    zIndex: Math.round(z + radius),
    '--card-depth': z
  }
}

// 更新所有卡片位置（直接操作 DOM）
const updateAllCards = () => {
  const total = props.models.length
  if (total === 0) return

  let updatedCount = 0
  for (let i = 0; i < total; i++) {
    const el = cardRefs[i]
    if (!el) continue

    const style = getCardStyle(i, total)
    el.style.transform = style.transform
    el.style.opacity = style.opacity
    el.style.zIndex = style.zIndex
    el.style.setProperty('--card-depth', style['--card-depth'])
    updatedCount++
  }

  // 如果没有更新任何卡片，说明 refs 还没准备好
  if (updatedCount === 0 && total > 0) {
    console.warn('No card refs found, total models:', total)
  }
}

// 选择卡片
const selectCard = (index) => {
  if (isLocked.value) return
  activeIndex.value = index

  // 旋转球体使选中的卡片朝向前方
  const total = props.models.length
  const phi = Math.acos(1 - 2 * (index + 0.5) / total)
  const theta = Math.PI * (1 + Math.sqrt(5)) * (index + 0.5)

  targetRotationX = -phi + Math.PI / 2
  targetRotationY = -theta
}

// 确认选择
const confirmSelect = () => {
  if (!currentModel.value || isLocked.value) return

  isLocked.value = true

  if (particleEngine) {
    particleEngine.burst(0, 0, 100)
  }

  setTimeout(() => {
    emit('select', currentModel.value)
  }, 600)
}

// 动画循环
const animate = () => {
  // 自动旋转
  if (isAutoRotating && !isLocked.value) {
    rotationY += autoRotateSpeed
  }

  // 平滑过渡到目标旋转
  rotationX += (targetRotationX - rotationX) * 0.05
  rotationY += (targetRotationY - rotationY) * 0.05

  // 直接更新 DOM
  updateAllCards()

  animationFrameId = requestAnimationFrame(animate)
}

// 手势模式切换
const onGestureModeChange = async (enabled) => {
  console.log('Gesture mode changed:', enabled)
  if (enabled) {
    const ok = await startGesture()
    console.log('Gesture start result:', ok)
    if (!ok) {
      gestureMode.value = false
    }
  } else {
    stopGesture()
  }
}

// 启动手势检测
const startGesture = async () => {
  if (!videoEl.value || !handCanvas.value) {
    console.error('Video or canvas element not found')
    return false
  }

  if (!gestureDetector) {
    gestureDetector = new GestureDetector()
  }

  gestureDetector.onGesture((gesture) => {
    console.log('=== Gesture callback ===')
    console.log('Type:', gesture.type)
    console.log('Position:', gesture.position)
    console.log('Current rotationY:', rotationY.toFixed(3))
    console.log('isAutoRotating:', isAutoRotating)
    console.log('Models count:', props.models.length)

    gestureState.value = gesture.type

    if (particleEngine && gesture.position && gesture.type !== 'idle') {
      particleEngine.followHand(gesture.position.x, gesture.position.y)
    }

    if (gesture.type === 'woodpecker') {
      isAutoRotating = false
      // 手在左边 (x < 0.5) 向右转，手在右边向左转
      const direction = gesture.position.x < 0.5 ? 1 : -1
      const oldRotation = rotationY
      rotationY += direction * 0.15
      console.log('>>> WOODPECKER ROTATION <<<')
      console.log('Direction:', direction, '(hand x:', gesture.position.x.toFixed(2) + ')')
      console.log('Old rotationY:', oldRotation.toFixed(3))
      console.log('New rotationY:', rotationY.toFixed(3))

      if (particleEngine) {
        particleEngine.emitRotateParticles(direction)
      }
    } else if (gesture.type === 'open') {
      isAutoRotating = false
      console.log('>>> OPEN HAND - STOP ROTATION <<<')
      if (particleEngine) {
        particleEngine.pulse()
      }
    } else if (gesture.type === 'fist') {
      console.log('>>> FIST - LOCK MODEL <<<')
      if (!isLocked.value) {
        confirmSelect()
      }
    } else if (gesture.type === 'idle') {
      isAutoRotating = true
    }
  })

  return await gestureDetector.start(videoEl.value, handCanvas.value)
}

// 停止手势检测
const stopGesture = () => {
  if (gestureDetector) {
    gestureDetector.stop()
  }
  gestureState.value = 'idle'
  isAutoRotating = true
}

// 初始化粒子引擎
const initParticles = () => {
  if (!particleCanvas.value || !containerRef.value) return

  const rect = containerRef.value.getBoundingClientRect()
  particleEngine = new SphereParticleEngine(particleCanvas.value)
  particleEngine.resize(rect.width, rect.height)
  particleEngine.start()
}

// 窗口大小变化
const onResize = () => {
  if (!particleCanvas.value || !containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  particleEngine?.resize(rect.width, rect.height)
}

// 监听模型列表变化
watch(() => props.models, (newModels) => {
  console.log('Models changed:', newModels?.length)
  activeIndex.value = 0
  isLocked.value = false
  rotationX = 0
  rotationY = 0
  targetRotationX = 0
  targetRotationY = 0

  // 等待 DOM 更新后重新初始化卡片位置
  nextTick(() => {
    console.log('After models change, cardRefs:', Object.keys(cardRefs).length)
    updateAllCards()
  })
}, { immediate: true })

onMounted(() => {
  console.log('=== SphereModelSelector mounted ===')
  console.log('Models count:', props.models.length)

  nextTick(() => {
    console.log('After nextTick, cardRefs:', Object.keys(cardRefs).length)
    initParticles()
    // 初始化卡片位置
    updateAllCards()
    animate()
    console.log('Animation started')
  })
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  stopGesture()
  if (particleEngine) {
    particleEngine.stop()
    particleEngine = null
  }
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', onResize)
})
</script>

<style lang="scss" scoped>
// 全息投影配色
$holo-bg: rgba(0, 15, 30, 0.92);
$holo-border: rgba(0, 255, 255, 0.4);
$holo-glow: rgba(0, 255, 255, 0.25);
$holo-text: #e0f7fa;
$holo-accent: #00ffff;
$holo-gold: #ffd700;
$holo-scanline: rgba(0, 255, 255, 0.08);

.sphere-selector {
  position: relative;
  min-height: 600px;
  user-select: none;
  perspective: 1200px;
  overflow: hidden;
}

// 粒子层
.particle-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

// 3D 球体容器
.sphere-container {
  position: relative;
  width: 100%;
  height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform-style: preserve-3d;
  z-index: 2;
}

// 中心光晕
.center-glow {
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(0, 255, 255, 0.15) 0%,
    rgba(0, 255, 255, 0.05) 40%,
    transparent 70%
  );
  pointer-events: none;
  animation: pulse-glow 4s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 1; }
}

// 球面上的卡片
.sphere-card {
  position: absolute;
  width: 180px;
  min-height: 140px;
  border: 1px solid $holo-border;
  border-radius: 8px;
  background: $holo-bg;
  color: $holo-text;
  overflow: hidden;
  cursor: pointer;
  transform-style: preserve-3d;
  backface-visibility: hidden;
  transition: box-shadow 0.3s, border-color 0.3s;
  // 初始位置在中心
  left: 50%;
  top: 50%;
  margin-left: -90px;
  margin-top: -70px;

  // 卡片光晕
  .card-glow {
    position: absolute;
    inset: -2px;
    border-radius: 10px;
    background: linear-gradient(
      135deg,
      rgba(0, 255, 255, 0.3) 0%,
      transparent 50%,
      rgba(0, 255, 255, 0.1) 100%
    );
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
    z-index: -1;
  }

  // 扫描线
  .card-scanline {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, $holo-accent, transparent);
    opacity: 0.6;
    animation: scanline 3s linear infinite;
    z-index: 2;
  }

  // 卡片阴影（3D 效果）
  .card-shadow {
    position: absolute;
    bottom: -20px;
    left: 10%;
    right: 10%;
    height: 20px;
    background: radial-gradient(
      ellipse at center,
      rgba(0, 255, 255, 0.2) 0%,
      transparent 70%
    );
    filter: blur(8px);
    opacity: calc(0.5 + var(--card-depth, 0) / 560);
    pointer-events: none;
  }

  &:hover {
    .card-glow {
      opacity: 1;
    }
  }

  &.active {
    border-color: $holo-accent;
    box-shadow:
      0 0 30px $holo-glow,
      0 0 60px rgba(0, 255, 255, 0.15),
      inset 0 0 20px rgba(0, 255, 255, 0.05);

    .card-glow {
      opacity: 1;
    }
  }

  &.locked {
    border-color: $holo-gold;
    box-shadow:
      0 0 30px rgba(255, 215, 0, 0.4),
      0 0 60px rgba(255, 215, 0, 0.2),
      inset 0 0 20px rgba(255, 215, 0, 0.05);

    .card-scanline {
      background: linear-gradient(90deg, transparent, $holo-gold, transparent);
    }
  }
}

@keyframes scanline {
  0% { top: -2px; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { top: 100%; opacity: 0; }
}

// 卡片内容
.card-content {
  padding: 16px;
  position: relative;
  z-index: 2;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.card-icon {
  font-size: 18px;
  color: $holo-accent;
  text-shadow: 0 0 8px $holo-glow;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: $holo-text;
  text-shadow: 0 0 6px $holo-glow;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, $holo-border, transparent);
  margin: 8px 0;
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.info-label {
  color: rgba(0, 255, 255, 0.5);
}

.info-value {
  color: $holo-text;
  font-weight: 500;
}

// 空状态 & 加载状态
.empty-state,
.loading-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: $holo-accent;
  opacity: 0.6;
  z-index: 10;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    animation: float 3s ease-in-out infinite;
  }

  p {
    font-size: 16px;
    margin-top: 8px;
  }

  .empty-hint {
    font-size: 13px;
    color: rgba(0, 255, 255, 0.4);
  }
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 255, 255, 0.2);
  border-top-color: $holo-accent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

// 底部控制栏
.control-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 16px;
  position: relative;
  z-index: 3;
}

// 当前模型指示
.current-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid $holo-border;
  border-radius: 20px;

  .indicator-label {
    font-size: 12px;
    color: rgba(0, 255, 255, 0.6);
  }

  .indicator-value {
    font-size: 14px;
    font-weight: 600;
    color: $holo-accent;
  }
}

// 手势控制区
.gesture-section {
  display: flex;
  align-items: center;
  gap: 12px;

  :deep(.el-switch) {
    --el-switch-on-color: rgba(0, 255, 255, 0.6);
    --el-switch-off-color: rgba(255, 255, 255, 0.2);
  }

  :deep(.el-switch__label) {
    color: rgba(0, 255, 255, 0.7);
    font-size: 12px;
  }
}

// 摄像头预览
.camera-preview {
  position: relative;
  width: 120px;
  height: 90px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid $holo-border;

  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: scaleX(-1);
  }

  .hand-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    transform: scaleX(-1);
  }

  .camera-border {
    position: absolute;
    inset: 0;
    border: 1px solid $holo-border;
    border-radius: 6px;
    pointer-events: none;
    box-shadow: inset 0 0 10px rgba(0, 255, 255, 0.1);
  }
}

// 手势状态
.gesture-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(0, 255, 255, 0.7);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transition: background 0.3s, box-shadow 0.3s;

  &.idle { background: rgba(255, 255, 255, 0.3); }
  &.open { background: #00ffff; box-shadow: 0 0 8px rgba(0, 255, 255, 0.6); }
  &.fist { background: #ffd700; box-shadow: 0 0 8px rgba(255, 215, 0, 0.6); }
  &.woodpecker { background: #4fc3f7; box-shadow: 0 0 8px rgba(79, 195, 247, 0.6); animation: pulse 0.5s infinite; }
  &.swipe_left, &.swipe_right { background: #4fc3f7; box-shadow: 0 0 6px rgba(79, 195, 247, 0.5); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.3); }
}

// 确认按钮
.confirm-btn {
  background: rgba(0, 255, 255, 0.15) !important;
  border-color: $holo-border !important;
  color: $holo-accent !important;
  font-weight: 600;
  transition: background 0.3s, box-shadow 0.3s;

  &:hover:not(:disabled) {
    background: rgba(0, 255, 255, 0.25) !important;
    box-shadow: 0 0 15px $holo-glow;
  }

  &:disabled {
    opacity: 0.4;
  }

  .locked-text {
    color: $holo-gold;
  }
}

// 手势提示
.gesture-hints {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 8px;
  position: relative;
  z-index: 3;
}

.hint-item {
  font-size: 12px;
  color: rgba(0, 255, 255, 0.5);
  display: flex;
  align-items: center;
  gap: 4px;

  .hint-icon {
    font-size: 16px;
  }
}
</style>
