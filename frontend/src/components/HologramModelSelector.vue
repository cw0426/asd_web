<template>
  <div class="hologram-selector" ref="selectorRef">
    <!-- 粒子 Canvas 层 -->
    <canvas ref="particleCanvas" class="particle-layer" />

    <!-- 全息卡片轮播区 -->
    <div class="carousel-wrapper" v-if="models.length > 0">
      <!-- 左箭头 -->
      <div class="nav-btn left" @click="prev" :class="{ disabled: currentIndex === 0 || isAnimating }">
        <span class="arrow">&#9664;</span>
      </div>

      <!-- 卡片区域 - 使用 overflow:hidden 的滑动舞台 -->
      <div class="carousel-viewport">
        <!-- 滑动轨道：通过 translateX 实现整体平移 -->
        <div
          class="carousel-track"
          :class="{ 'no-transition': !smoothEnabled }"
          :style="trackStyle"
          @transitionend="onTrackTransitionEnd"
        >
          <!-- 渲染当前可见范围 + 缓冲的卡片 -->
          <div
            v-for="offset in visibleOffsets"
            :key="currentIndex + offset"
            class="hologram-card"
            :class="getCardClass(offset)"
            @click="handleCardClick(offset)"
          >
            <div class="card-scanline" />
            <template v-if="offset === 0">
              <!-- 中心卡片 - 完整内容 -->
              <div class="card-corner tl" />
              <div class="card-corner tr" />
              <div class="card-corner bl" />
              <div class="card-corner br" />
              <div class="card-content" v-if="currentModel">
                <div class="card-header">
                  <div class="card-icon">&#9881;</div>
                  <div class="card-name">{{ currentModel.name }}</div>
                </div>
                <div class="card-divider" />
                <div class="card-info">
                  <div class="info-row">
                    <span class="info-label">池化方法</span>
                    <span class="info-value">{{ currentModel.pooling_method }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">训练集</span>
                    <span class="info-value">{{ currentModel.train_dataset }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">类别数</span>
                    <span class="info-value">{{ currentModel.num_classes }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">嵌入维度</span>
                    <span class="info-value">{{ currentModel.embedding_dim }}</span>
                  </div>
                  <div class="info-row">
                    <span class="info-label">损失函数</span>
                    <span class="info-value">{{ currentModel.loss_func }}</span>
                  </div>
                </div>
                <div class="card-divider" />
                <div class="card-footer">
                  <span>Query: {{ currentModel.query }}</span>
                  <span>{{ formatTime(currentModel.create_time) }}</span>
                </div>
              </div>
            </template>
            <template v-else>
              <!-- 侧边卡片 - 简约内容 -->
              <div class="card-content">
                <div class="card-name">{{ getModelAt(currentIndex + offset)?.name }}</div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 右箭头 -->
      <div class="nav-btn right" @click="next" :class="{ disabled: currentIndex === models.length - 1 || isAnimating }">
        <span class="arrow">&#9654;</span>
      </div>
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
      <!-- 指示点 -->
      <div class="indicator-dots">
        <span
          v-for="(_, idx) in models"
          :key="idx"
          class="dot"
          :class="{ active: idx === currentIndex }"
          @click="goTo(idx)"
        />
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
        :disabled="!currentModel"
        @click="confirmSelect"
      >
        <span v-if="!isLocked">&#10003; 确认选择</span>
        <span v-else class="locked-text">&#128274; 已锁定</span>
      </el-button>
    </div>

    <!-- 手势操作提示 -->
    <div class="gesture-hints" v-show="gestureMode">
      <div class="hint-item"><span class="hint-icon">&#9995;&#8592;&#9995;</span> 左右滑动切换</div>
      <div class="hint-item"><span class="hint-icon">&#9994;</span> 握拳确认选择</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ParticleEngine } from '@/utils/particleEngine'
import { GestureDetector } from '@/utils/gestureDetector'

const props = defineProps({
  models: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

// Refs
const selectorRef = ref(null)
const particleCanvas = ref(null)
const centerCardRef = ref(null)
const videoEl = ref(null)
const handCanvas = ref(null)

// 状态
const currentIndex = ref(0)
const isLocked = ref(false)
const gestureMode = ref(false)
const gestureState = ref('idle')

// 滑动状态
const slideOffset = ref(0)        // 当前滑动的偏移量（-1, 0, 1）
const isAnimating = ref(false)     // 是否正在动画中
const smoothEnabled = ref(true)    // 是否启用 CSS transition
const ANIM_DURATION = 480          // 动画时长 ms

// 粒子引擎 & 手势检测
let particleEngine = null
let gestureDetector = null

// 计算属性
const currentModel = computed(() => props.models[currentIndex.value])
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < props.models.length - 1)

// 渲染的卡片偏移量：-2, -1, 0, 1, 2（两侧各多一个用于滑入缓冲）
const visibleOffsets = computed(() => {
  const offsets = [0]
  if (currentIndex.value > 0) offsets.push(-1)
  if (currentIndex.value > 1) offsets.push(-2)
  if (currentIndex.value < props.models.length - 1) offsets.push(1)
  if (currentIndex.value < props.models.length - 2) offsets.push(2)
  return offsets.sort((a, b) => a - b)
})

// 轨道样式：通过 translateX 控制整体位移
const trackStyle = computed(() => {
  // slideOffset 控制动画偏移，0 = 居中，-1 = 向左滑了一格，1 = 向右滑了一格
  const x = -slideOffset.value * 340 // 340 = 320(卡片宽) + 20(gap)
  return {
    transform: `translateX(${x}px)`
  }
})

const gestureStatusText = computed(() => {
  const map = {
    idle: '等待手势...',
    open: '手掌张开',
    fist: '握拳 - 确认选择',
    swipe_left: '左滑 - 上一个',
    swipe_right: '右滑 - 下一个'
  }
  return map[gestureState.value] || '等待手势...'
})

// 获取指定索引的模型
const getModelAt = (idx) => {
  if (idx < 0 || idx >= props.models.length) return null
  return props.models[idx]
}

// 卡片样式类
const getCardClass = (offset) => {
  const cls = []
  if (offset === 0) {
    cls.push('center-card')
    if (isLocked.value) cls.push('locked')
  } else {
    cls.push('side-card')
    if (offset < 0) cls.push('left-card')
    else cls.push('right-card')
    // 滑出视口的卡片隐藏
    if (Math.abs(offset) > 1) cls.push('buffer-card')
  }
  return cls
}

// 点击卡片
const handleCardClick = (offset) => {
  if (offset < 0) prev()
  else if (offset > 0) next()
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  const utcTime = time.endsWith('Z') ? time : time + 'Z'
  const date = new Date(utcTime)
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

// ===== 滑动切换逻辑 =====

// 切换到下一个（向左滑，卡片向左移动）
const next = () => {
  if (currentIndex.value >= props.models.length - 1 || isLocked.value || isAnimating.value) return
  animateSlide('left')
}

// 切换到上一个（向右滑，卡片向右移动）
const prev = () => {
  if (currentIndex.value <= 0 || isLocked.value || isAnimating.value) return
  animateSlide('right')
}

// 跳转到指定索引
const goTo = (idx) => {
  if (idx === currentIndex.value || isLocked.value || isAnimating.value) return
  const direction = idx > currentIndex.value ? 'left' : 'right'
  const steps = Math.abs(idx - currentIndex.value)
  if (steps === 1) {
    animateSlide(direction)
  } else {
    // 多步跳转直接切换，不做动画
    smoothEnabled.value = false
    currentIndex.value = idx
    nextTick(() => {
      smoothEnabled.value = true
      updateOrbitParticles()
    })
  }
}

// 执行滑动动画
const animateSlide = (direction) => {
  isAnimating.value = true
  smoothEnabled.value = true

  // 设置偏移量触发 CSS transition
  // 向左滑 → slideOffset = -1（轨道左移，右边卡片滑入中心）
  // 向右滑 → slideOffset = 1（轨道右移，左边卡片滑入中心）
  slideOffset.value = direction === 'left' ? -1 : 1

  // 粒子拖尾效果（减少粒子数）
  emitTrailParticles(direction)
}

// 轨道动画结束回调
const onTrackTransitionEnd = () => {
  if (!isAnimating.value) return

  // 关闭 transition，防止数据更新时再次触发动画
  smoothEnabled.value = false

  // 根据滑动方向更新索引
  if (slideOffset.value === -1) {
    currentIndex.value++
  } else if (slideOffset.value === 1) {
    currentIndex.value--
  }

  // 重置偏移量（此时 transition 已关闭，不会触发动画）
  slideOffset.value = 0

  // 解锁
  isLocked.value = false

  // 下一帧重新启用 transition
  nextTick(() => {
    smoothEnabled.value = true
    isAnimating.value = false
    updateOrbitParticles()
  })
}

// 粒子拖尾（减少数量避免卡顿）
const emitTrailParticles = (direction) => {
  if (!particleEngine || !centerCardRef.value || !selectorRef.value) return

  const rect = centerCardRef.value.getBoundingClientRect()
  const selectorRect = selectorRef.value.getBoundingClientRect()
  const cx = rect.left - selectorRect.left + rect.width / 2
  const cy = rect.top - selectorRect.top + rect.height / 2

  const fromX = direction === 'left' ? cx + 150 : cx - 150
  const toX = direction === 'left' ? cx - 150 : cx + 150
  particleEngine.trail(fromX, cy, toX, cy, 12)
}

// 确认选择
const confirmSelect = () => {
  if (!currentModel.value || isLocked.value || isAnimating.value) return

  isLocked.value = true

  // 粒子爆发效果
  if (particleEngine && centerCardRef.value && selectorRef.value) {
    const rect = centerCardRef.value.getBoundingClientRect()
    const selectorRect = selectorRef.value.getBoundingClientRect()
    const cx = rect.left - selectorRect.left + rect.width / 2
    const cy = rect.top - selectorRect.top + rect.height / 2
    particleEngine.burst(cx, cy, 80)
  }

  setTimeout(() => {
    emit('select', currentModel.value)
  }, 500)
}

// 键盘控制
const onKeyDown = (e) => {
  if (e.key === 'ArrowLeft') prev()
  else if (e.key === 'ArrowRight') next()
  else if (e.key === 'Enter') confirmSelect()
}

// 手势模式切换
const onGestureModeChange = async (enabled) => {
  if (enabled) {
    const ok = await startGesture()
    if (!ok) {
      gestureMode.value = false
    }
  } else {
    stopGesture()
  }
}

// 启动手势检测
const startGesture = async () => {
  if (!videoEl.value || !handCanvas.value) return false

  if (!gestureDetector) {
    gestureDetector = new GestureDetector()
  }

  gestureDetector.onGesture((gesture) => {
    gestureState.value = gesture.type

    // 粒子跟随手掌
    if (particleEngine && gesture.position && gesture.type !== 'idle') {
      const selectorRect = selectorRef.value?.getBoundingClientRect()
      if (selectorRect) {
        const x = (1 - gesture.position.x) * selectorRect.width
        const y = gesture.position.y * selectorRect.height
        particleEngine.followFinger(x, y, 2)
      }
    }

    if (gesture.type === 'swipe_left') {
      prev()
    } else if (gesture.type === 'swipe_right') {
      next()
    } else if (gesture.type === 'fist') {
      confirmSelect()
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
}

// 初始化粒子引擎
const initParticles = () => {
  if (!particleCanvas.value || !selectorRef.value) return

  const rect = selectorRef.value.getBoundingClientRect()
  particleEngine = new ParticleEngine(particleCanvas.value)
  particleEngine.resize(rect.width, rect.height)
  particleEngine.start()

  updateOrbitParticles()
}

// 更新环绕粒子位置
const updateOrbitParticles = () => {
  if (!particleEngine || !selectorRef.value) return

  // 找到中心卡片
  const centerEl = selectorRef.value.querySelector('.center-card')
  if (!centerEl) return

  const cardRect = centerEl.getBoundingClientRect()
  const selectorRect = selectorRef.value.getBoundingClientRect()
  const cx = cardRect.left - selectorRect.left + cardRect.width / 2
  const cy = cardRect.top - selectorRect.top + cardRect.height / 2
  const radius = Math.max(cardRect.width, cardRect.height) * 0.6

  particleEngine.startOrbit(cx, cy, radius)
}

// 监听模型列表变化，重新初始化粒子
watch(() => props.models, () => {
  currentIndex.value = 0
  isLocked.value = false
  slideOffset.value = 0
  nextTick(() => {
    updateOrbitParticles()
  })
})

// 窗口大小变化
const onResize = () => {
  if (!particleCanvas.value || !selectorRef.value) return
  const rect = selectorRef.value.getBoundingClientRect()
  particleEngine?.resize(rect.width, rect.height)
}

onMounted(() => {
  nextTick(() => {
    initParticles()
  })
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  stopGesture()
  if (particleEngine) {
    particleEngine.stop()
    particleEngine = null
  }
  window.removeEventListener('keydown', onKeyDown)
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

// 滑动过渡曲线：先快后慢的减速曲线
$slide-ease: cubic-bezier(0.22, 1, 0.36, 1);
$slide-duration: 0.48s;

.hologram-selector {
  position: relative;
  min-height: 420px;
  user-select: none;
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

// 轮播包装
.carousel-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  position: relative;
  z-index: 2;
}

// 导航按钮
.nav-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid $holo-border;
  background: rgba(0, 20, 40, 0.6);
  color: $holo-accent;
  cursor: pointer;
  transition: background 0.3s, box-shadow 0.3s;
  flex-shrink: 0;
  z-index: 5;

  .arrow {
    font-size: 16px;
  }

  &:hover:not(.disabled) {
    background: rgba(0, 255, 255, 0.15);
    box-shadow: 0 0 15px $holo-glow;
  }

  &.disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
}

// 卡片视口 - 裁剪溢出
.carousel-viewport {
  overflow: hidden;
  flex: 1;
  max-width: 800px;
  margin: 0 8px;
  perspective: 1000px;
}

// 滑动轨道 - 通过 translateX 整体平移
.carousel-track {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  // 核心：transform transition 实现丝滑滑动
  transition: transform $slide-duration $slide-ease;
  will-change: transform;

  &.no-transition {
    transition: none !important;
  }
}

// 全息卡片基础
.hologram-card {
  position: relative;
  border: 1px solid $holo-border;
  border-radius: 8px;
  background: $holo-bg;
  color: $holo-text;
  overflow: hidden;
  // 仅对 opacity 做过渡（transform 由轨道控制）
  transition: opacity $slide-duration $slide-ease, box-shadow $slide-duration $slide-ease;
  will-change: opacity;
  // GPU 加速
  backface-visibility: hidden;
  flex-shrink: 0;

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

  // 四角装饰
  .card-corner {
    position: absolute;
    width: 12px;
    height: 12px;
    border-color: $holo-accent;
    border-style: solid;
    z-index: 3;

    &.tl { top: 4px; left: 4px; border-width: 2px 0 0 2px; }
    &.tr { top: 4px; right: 4px; border-width: 2px 2px 0 0; }
    &.bl { bottom: 4px; left: 4px; border-width: 0 0 2px 2px; }
    &.br { bottom: 4px; right: 4px; border-width: 0 2px 2px 0; }
  }
}

@keyframes scanline {
  0% { top: -2px; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { top: 100%; opacity: 0; }
}

// 中心卡片
.center-card {
  width: 320px;
  min-height: 260px;
  opacity: 1;
  box-shadow:
    0 0 20px $holo-glow,
    0 0 60px rgba(0, 255, 255, 0.1),
    inset 0 0 30px rgba(0, 255, 255, 0.05);

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      $holo-scanline 2px,
      $holo-scanline 4px
    );
    pointer-events: none;
    z-index: 1;
  }

  &.locked {
    border-color: $holo-gold;
    box-shadow:
      0 0 25px rgba(255, 215, 0, 0.4),
      0 0 80px rgba(255, 215, 0, 0.15),
      inset 0 0 30px rgba(255, 215, 0, 0.05);

    .card-corner { border-color: $holo-gold; }
    .card-scanline { background: linear-gradient(90deg, transparent, $holo-gold, transparent); }
  }
}

// 侧边卡片
.side-card {
  width: 200px;
  min-height: 160px;
  opacity: 0.5;
  cursor: pointer;
  // 3D 透视由各侧卡片单独控制
  &.left-card {
    transform: perspective(800px) rotateY(25deg) scale(0.85);
  }

  &.right-card {
    transform: perspective(800px) rotateY(-25deg) scale(0.85);
  }

  &:hover {
    opacity: 0.7;
    box-shadow: 0 0 15px $holo-glow;
  }

  .card-content {
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
  }

  .card-name {
    font-size: 14px;
    text-align: center;
    word-break: break-all;
  }
}

// 缓冲卡片（视口外的，仅用于滑入动画，不可见）
.buffer-card {
  opacity: 0 !important;
  pointer-events: none;
}

// 卡片内容
.card-content {
  padding: 24px;
  position: relative;
  z-index: 2;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.card-icon {
  font-size: 24px;
  color: $holo-accent;
  text-shadow: 0 0 10px $holo-glow;
}

.card-name {
  font-size: 18px;
  font-weight: 600;
  color: $holo-text;
  text-shadow: 0 0 8px $holo-glow;
}

.card-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, $holo-border, transparent);
  margin: 12px 0;
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-label {
  color: rgba(0, 255, 255, 0.6);
}

.info-value {
  color: $holo-text;
  font-weight: 500;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(0, 255, 255, 0.5);
}

// 空状态 & 加载状态
.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: $holo-accent;
  opacity: 0.6;

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
  margin-top: 16px;
  padding: 16px;
  position: relative;
  z-index: 3;
}

// 指示点
.indicator-dots {
  display: flex;
  gap: 8px;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.25);
  cursor: pointer;
  transition: all 0.3s;

  &.active {
    background: $holo-accent;
    box-shadow: 0 0 8px $holo-glow;
    transform: scale(1.3);
  }

  &:hover:not(.active) {
    background: rgba(0, 255, 255, 0.5);
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
  transition: background 0.3s;

  &.idle { background: rgba(255, 255, 255, 0.3); }
  &.open { background: #00ffff; box-shadow: 0 0 6px rgba(0, 255, 255, 0.5); }
  &.fist { background: #ffd700; box-shadow: 0 0 6px rgba(255, 215, 0, 0.5); }
  &.swipe_left, &.swipe_right { background: #4fc3f7; box-shadow: 0 0 6px rgba(79, 195, 247, 0.5); }
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
  margin-top: 8px;
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
