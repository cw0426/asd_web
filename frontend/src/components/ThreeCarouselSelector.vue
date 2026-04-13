<template>
  <div class="three-carousel-selector" ref="containerRef">
    <!-- Three.js 渲染容器 -->
    <div ref="threeContainer" class="three-container" />

    <!-- 粒子 Canvas 层 -->
    <canvas ref="particleCanvas" class="particle-layer" />

    <!-- UI 状态层 -->
    <div class="ui-layer">
      <div class="status-row">
        <span class="status-label">视觉捕获引擎:</span>
        <span class="status-value" :class="visionReady ? 'ready' : 'loading'">
          {{ visionReady ? '追踪正常' : '启动中...' }}
        </span>
      </div>
      <div class="status-row">
        <span class="status-label">当前交互状态:</span>
        <span class="status-value">{{ gestureStatusText }}</span>
      </div>
      <div class="status-row" style="margin-top: 16px;">
        <span class="status-label">当前锁定节点:</span>
        <span class="status-value highlight">{{ lockedModelName }}</span>
      </div>
    </div>

    <!-- 手势操作提示 -->
    <div class="gesture-instructions" v-show="gestureMode">
      <div class="instruction-item">
        <span class="instruction-icon">&#128076;</span>
        OK 手势：驱动轮播旋转
      </div>
      <div class="instruction-item">
        <span class="instruction-icon">&#9994;</span>
        握拳：锁定当前模型
      </div>
      <div class="instruction-item">
        <span class="instruction-icon">&#128400;</span>
        张开手掌：解锁并停止旋转
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
      </div>

      <!-- 确认按钮 -->
      <el-button
        type="primary"
        class="confirm-btn"
        :disabled="!currentModel"
        @click="confirmSelect"
      >
        <span v-if="!isLocked">&#10003; 确认选择</span>
        <span v-else class="locked-text">&#10003; 已锁定，点击确认</span>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { GestureDetector } from '@/utils/gestureDetector'

const props = defineProps({
  models: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

// Refs
const containerRef = ref(null)
const threeContainer = ref(null)
const particleCanvas = ref(null)
const videoEl = ref(null)
const handCanvas = ref(null)

// 状态
const gestureMode = ref(false)
const isLocked = ref(false)
const visionReady = ref(false)
const currentGesture = ref('idle')
const lockedModelName = ref('[ 未锁定 ]')

// Three.js 变量
let scene = null
let camera = null
let renderer = null
let carouselGroup = null
let cards = []
let isRotating = false
let animationFrameId = null
let backgroundParticles = null
let glowTime = 0

// 手势检测
let gestureDetector = null

// 计算属性
const currentModel = computed(() => {
  if (cards.length === 0) return null
  // 找到最前面的卡片
  let closestCard = null
  let maxZ = -Infinity
  const tempVec = new THREE.Vector3()

  cards.forEach(card => {
    card.getWorldPosition(tempVec)
    if (tempVec.z > maxZ) {
      maxZ = tempVec.z
      closestCard = card
    }
  })

  return closestCard ? closestCard.userData.modelData : null
})

const gestureStatusText = computed(() => {
  const map = {
    idle: '等待输入',
    OK: 'OK (驱动旋转)',
    FIST: '握拳 (锁定模型)',
    OPEN_PALM: '张掌 (解锁)'
  }
  return map[currentGesture.value] || '等待输入'
})

// 创建卡片贴图（带流光效果）
function createCardTexture(model, isSelected = false, glowOffset = 0) {
  const canvas = document.createElement('canvas')
  canvas.width = 320
  canvas.height = 480
  const ctx = canvas.getContext('2d')

  // 基础背景 - 玻璃拟态
  ctx.fillStyle = isSelected ? 'rgba(255, 107, 107, 0.15)' : 'rgba(255, 255, 255, 0.12)'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // 流光效果 - 从左到右的光带
  const glowGradient = ctx.createLinearGradient(
    glowOffset - 100, 0, glowOffset + 100, 0
  )
  glowGradient.addColorStop(0, 'transparent')
  glowGradient.addColorStop(0.5, isSelected ? 'rgba(255, 107, 107, 0.4)' : 'rgba(255, 217, 61, 0.3)')
  glowGradient.addColorStop(1, 'transparent')
  ctx.fillStyle = glowGradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // 外边框
  ctx.strokeStyle = isSelected ? '#FF6B6B' : 'rgba(255, 255, 255, 0.5)'
  ctx.lineWidth = isSelected ? 3 : 2
  ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4)

  // 科技感角标
  ctx.lineWidth = 2
  const cornerLen = 30
  ctx.strokeStyle = isSelected ? '#FF6B6B' : '#FFD93D'
  ctx.beginPath()
  // 左上
  ctx.moveTo(10, 10 + cornerLen); ctx.lineTo(10, 10); ctx.lineTo(10 + cornerLen, 10)
  // 右上
  ctx.moveTo(canvas.width - 10 - cornerLen, 10); ctx.lineTo(canvas.width - 10, 10); ctx.lineTo(canvas.width - 10, 10 + cornerLen)
  // 左下
  ctx.moveTo(10, canvas.height - 10 - cornerLen); ctx.lineTo(10, canvas.height - 10); ctx.lineTo(10 + cornerLen, canvas.height - 10)
  // 右下
  ctx.moveTo(canvas.width - 10 - cornerLen, canvas.height - 10); ctx.lineTo(canvas.width - 10, canvas.height - 10); ctx.lineTo(canvas.width - 10, canvas.height - 10 - cornerLen)
  ctx.stroke()

  // 主标题
  ctx.fillStyle = isSelected ? '#FF6B6B' : '#2d3748'
  ctx.textAlign = 'center'
  ctx.font = 'bold 22px sans-serif'
  ctx.fillText(model.name || 'Unknown Model', canvas.width / 2, 55)

  // 分隔线
  const lineGradient = ctx.createLinearGradient(40, 0, canvas.width - 40, 0)
  lineGradient.addColorStop(0, 'transparent')
  lineGradient.addColorStop(0.5, isSelected ? '#FF6B6B' : '#FFD93D')
  lineGradient.addColorStop(1, 'transparent')
  ctx.strokeStyle = lineGradient
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(40, 85)
  ctx.lineTo(canvas.width - 40, 85)
  ctx.stroke()

  // 状态指示
  ctx.font = '13px sans-serif'
  ctx.textAlign = 'left'
  ctx.fillStyle = isSelected ? '#FF6B6B' : '#718096'
  ctx.fillText('STATUS: ' + (isSelected ? 'ACTIVE_LOCKED' : 'STANDBY'), 40, 120)

  // 模型信息
  ctx.fillStyle = '#2d3748'
  ctx.font = '14px sans-serif'
  const metrics = [
    `池化方法: ${model.pooling_method || '-'}`,
    `训练集: ${model.train_dataset || '-'}`,
    `类别数: ${model.num_classes || '-'}`,
    `嵌入维度: ${model.embedding_dim || '-'}`,
    `损失函数: ${model.loss_func || '-'}`
  ]

  let startY = 165
  metrics.forEach(m => {
    ctx.fillText(`> ${m}`, 40, startY)
    startY += 32
  })

  // 底部 ID
  ctx.textAlign = 'right'
  ctx.font = '11px monospace'
  ctx.fillStyle = '#718096'
  ctx.fillText(`ID: ${model.id || 'N/A'}`, canvas.width - 40, canvas.height - 25)

  return new THREE.CanvasTexture(canvas)
}

// 初始化 Three.js 场景
function initThreeScene() {
  if (!threeContainer.value) return

  const width = threeContainer.value.clientWidth
  const height = threeContainer.value.clientHeight

  // 场景
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x030504, 0.018)

  // 相机
  camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000)
  camera.position.z = 16

  // 渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  threeContainer.value.appendChild(renderer.domElement)

  // 创建背景粒子
  createBackgroundParticles()

  // 轮播组
  carouselGroup = new THREE.Group()
  scene.add(carouselGroup)

  // 创建卡片
  createCards()
}

// 创建背景粒子
function createBackgroundParticles() {
  const particleCount = 600
  const positions = new Float32Array(particleCount * 3)
  const sizes = new Float32Array(particleCount)

  for (let i = 0; i < particleCount; i++) {
    // 球形分布
    const radius = 15 + Math.random() * 30
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)

    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = radius * Math.cos(phi)

    sizes[i] = Math.random() * 2.5 + 0.5
  }

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  // 白色粒子着色器
  const material = new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      pixelRatio: { value: window.devicePixelRatio }
    },
    vertexShader: `
      attribute float size;
      uniform float time;
      uniform float pixelRatio;

      varying float vAlpha;

      void main() {
        vec3 pos = position;
        // 添加缓慢的漂浮动画
        pos.x += sin(time * 0.3 + position.y * 0.1) * 0.8;
        pos.y += cos(time * 0.2 + position.x * 0.1) * 0.8;
        pos.z += sin(time * 0.25 + position.z * 0.1) * 0.5;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);

        // 根据深度计算透明度
        vAlpha = smoothstep(-50.0, -5.0, mvPosition.z);

        gl_PointSize = size * pixelRatio * (180.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying float vAlpha;

      void main() {
        float dist = length(gl_PointCoord - vec2(0.5));
        if (dist > 0.5) discard;

        float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
        // 白色粒子
        gl_FragColor = vec4(1.0, 1.0, 1.0, alpha * vAlpha * 0.7);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  })

  backgroundParticles = new THREE.Points(geometry, material)
  scene.add(backgroundParticles)

  // 创建极光背景平面
  createAuroraBackground()
}

// 创建极光背景
function createAuroraBackground() {
  const geometry = new THREE.PlaneGeometry(100, 100)

  const material = new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 }
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      void main() {
        // 纯黑色背景
        gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
      }
    `,
    side: THREE.DoubleSide,
    depthWrite: false
  })

  const aurora = new THREE.Mesh(geometry, material)
  aurora.position.z = -40
  aurora.userData.isAurora = true
  scene.add(aurora)
}

// 创建卡片
function createCards() {
  if (!carouselGroup) return

  // 清除旧卡片
  cards.forEach(card => {
    carouselGroup.remove(card)
    card.geometry.dispose()
    card.material.dispose()
  })
  cards = []

  const totalCards = props.models.length
  if (totalCards === 0) return

  const radius = 9

  for (let i = 0; i < totalCards; i++) {
    const theta = (i / totalCards) * Math.PI * 2
    const x = radius * Math.sin(theta)
    const z = radius * Math.cos(theta)
    const y = 0

    const model = props.models[i]
    const geometry = new THREE.PlaneGeometry(3.2, 4.8)
    const material = new THREE.MeshBasicMaterial({
      map: createCardTexture(model, false, 0),
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false
    })

    const cardMesh = new THREE.Mesh(geometry, material)
    cardMesh.position.set(x, y, z)
    cardMesh.lookAt(x * 2, y, z * 2)
    cardMesh.userData = { modelData: model, index: i }

    carouselGroup.add(cardMesh)
    cards.push(cardMesh)
  }
}

// 选择最近的卡片
function selectClosestCard() {
  if (isLocked.value) return

  isRotating = false
  isLocked.value = true

  let closestCard = cards[0]
  let maxZ = -Infinity
  const tempVec = new THREE.Vector3()

  cards.forEach(card => {
    card.getWorldPosition(tempVec)
    if (tempVec.z > maxZ) {
      maxZ = tempVec.z
      closestCard = card
    }
  })

  // 更新所有卡片样式
  cards.forEach(card => {
    if (card !== closestCard) {
      card.material.map = createCardTexture(card.userData.modelData, false, 0)
      card.material.opacity = 0.15
    }
  })

  // 高亮选中的卡片
  closestCard.material.map = createCardTexture(closestCard.userData.modelData, true, 0)
  closestCard.material.opacity = 1.0

  lockedModelName.value = `[ ${closestCard.userData.modelData.name} ]`

  // 粒子爆发效果
  burstParticles()

  // 延迟后触发选择事件
  setTimeout(() => {
    emit('select', closestCard.userData.modelData)
  }, 600)
}

// 解除锁定
function unlockAll() {
  if (!isLocked.value) return

  isLocked.value = false
  lockedModelName.value = '[ 未锁定 ]'

  cards.forEach(card => {
    card.material.map = createCardTexture(card.userData.modelData, false, 0)
    card.material.opacity = 1.0
  })
}

// 粒子爆发效果
function burstParticles() {
  if (!particleCanvas.value || !containerRef.value) return

  const ctx = particleCanvas.value.getContext('2d')
  const rect = containerRef.value.getBoundingClientRect()

  // 创建爆发粒子
  const particles = []
  const centerX = rect.width / 2
  const centerY = rect.height / 2

  for (let i = 0; i < 60; i++) {
    const angle = Math.random() * Math.PI * 2
    const speed = 3 + Math.random() * 6
    particles.push({
      x: centerX,
      y: centerY,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 1,
      size: 2 + Math.random() * 3,
      color: Math.random() > 0.3 ? '#00ffff' : '#ffffff'
    })
  }

  // 动画
  let frame = 0
  const animateBurst = () => {
    ctx.clearRect(0, 0, particleCanvas.value.width, particleCanvas.value.height)

    let alive = false
    particles.forEach(p => {
      if (p.life <= 0) return
      alive = true

      p.x += p.vx
      p.y += p.vy
      p.vx *= 0.96
      p.vy *= 0.96
      p.life -= 0.02

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2)
      ctx.fillStyle = p.color
      ctx.globalAlpha = p.life
      ctx.fill()
    })

    ctx.globalAlpha = 1

    if (alive && frame < 60) {
      frame++
      requestAnimationFrame(animateBurst)
    }
  }

  animateBurst()
}

// 动画循环
function animate() {
  animationFrameId = requestAnimationFrame(animate)

  // 更新时间
  glowTime += 0.016

  // 更新背景粒子
  if (backgroundParticles) {
    backgroundParticles.material.uniforms.time.value = glowTime
    // 缓慢旋转背景粒子
    backgroundParticles.rotation.y += 0.0003
    backgroundParticles.rotation.x += 0.0001
  }

  // 更新极光背景
  if (scene) {
    scene.traverse((obj) => {
      if (obj.userData && obj.userData.isAurora && obj.material) {
        obj.material.uniforms.time.value = glowTime
      }
    })
  }

  // 旋转轮播 - 调整速度
  if (isRotating && carouselGroup) {
    carouselGroup.rotation.y -= 0.006 // 适中速度
  }

  // 更新卡片流光效果
  if (cards.length > 0 && !isLocked.value) {
    const glowOffset = (glowTime * 100) % 520 // 循环流光
    cards.forEach(card => {
      if (card.material.opacity > 0.5) {
        card.material.map = createCardTexture(card.userData.modelData, false, glowOffset)
        card.material.map.needsUpdate = true
      }
    })
  }

  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

// 手势检测
function detectGesture(landmarks) {
  const dist = (p1, p2) => Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2))
  const wrist = landmarks[0]
  const thumbTip = landmarks[4]
  const indexTip = landmarks[8]
  const middleTip = landmarks[12]
  const ringTip = landmarks[16]
  const pinkyTip = landmarks[20]

  // OK 手势：拇指和食指靠近
  if (dist(thumbTip, indexTip) < 0.07) return 'OK'

  // 握拳：所有指尖靠近手腕
  if (dist(indexTip, wrist) < 0.35 &&
      dist(middleTip, wrist) < 0.35 &&
      dist(ringTip, wrist) < 0.35 &&
      dist(pinkyTip, wrist) < 0.35) return 'FIST'

  return 'OPEN_PALM'
}

// 启动手势检测
async function startGesture() {
  if (!videoEl.value || !handCanvas.value) return false

  if (!gestureDetector) {
    gestureDetector = new GestureDetector()
  }

  // 使用自定义手势检测
  gestureDetector.onGesture((gesture) => {
    // 我们会覆盖这个回调
  })

  gestureDetector.onLandmarks((landmarks) => {
    if (!landmarks || landmarks.length === 0) {
      // 没有检测到手势时
      currentGesture.value = 'idle'
      // 只有未锁定时才停止旋转，锁定状态保持不变
      if (!isLocked.value) {
        isRotating = false
      }
      return
    }

    const gesture = detectGesture(landmarks)
    currentGesture.value = gesture

    if (gesture === 'FIST') {
      // 握拳：锁定模型
      isRotating = false
      selectClosestCard()
    } else if (gesture === 'OK') {
      // OK手势：旋转（不改变锁定状态）
      isRotating = true
    } else if (gesture === 'OPEN_PALM') {
      // 张开手掌：解锁并停止旋转
      unlockAll()
      isRotating = false
    }

    // 绘制手部关键点
    drawHandLandmarks(landmarks)
  })

  const success = await gestureDetector.start(videoEl.value, handCanvas.value)
  if (success) {
    visionReady.value = true
  }
  return success
}

// 绘制手部关键点
function drawHandLandmarks(landmarks) {
  if (!handCanvas.value) return

  const ctx = handCanvas.value.getContext('2d')
  const w = handCanvas.value.width
  const h = handCanvas.value.height

  ctx.clearRect(0, 0, w, h)

  if (!landmarks) return

  // 连接线
  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [0, 9], [9, 10], [10, 11], [11, 12],
    [0, 13], [13, 14], [14, 15], [15, 16],
    [0, 17], [17, 18], [18, 19], [19, 20],
    [5, 9], [9, 13], [13, 17]
  ]

  ctx.strokeStyle = '#00ffff'
  ctx.lineWidth = 2
  for (const [a, b] of connections) {
    ctx.beginPath()
    ctx.moveTo(landmarks[a].x * w, landmarks[a].y * h)
    ctx.lineTo(landmarks[b].x * w, landmarks[b].y * h)
    ctx.stroke()
  }

  // 关键点
  for (const lm of landmarks) {
    ctx.beginPath()
    ctx.arc(lm.x * w, lm.y * h, 3, 0, Math.PI * 2)
    ctx.fillStyle = '#00ffff'
    ctx.fill()
  }
}

// 停止手势检测
function stopGesture() {
  if (gestureDetector) {
    gestureDetector.stop()
  }
  visionReady.value = false
  currentGesture.value = 'idle'
  isRotating = false
}

// 手势模式切换
async function onGestureModeChange(enabled) {
  if (enabled) {
    const ok = await startGesture()
    if (!ok) {
      gestureMode.value = false
    }
  } else {
    stopGesture()
  }
}

// 确认选择
function confirmSelect() {
  if (!currentModel.value) return

  // 如果已经锁定，直接触发选择事件
  if (isLocked.value) {
    emit('select', currentModel.value)
    return
  }

  // 否则执行锁定流程
  selectClosestCard()
}

// 窗口大小变化
function onResize() {
  if (!threeContainer.value || !camera || !renderer) return

  const width = threeContainer.value.clientWidth
  const height = threeContainer.value.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)

  // 更新粒子 canvas
  if (particleCanvas.value && containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    particleCanvas.value.width = rect.width
    particleCanvas.value.height = rect.height
  }
}

// 监听模型列表变化
watch(() => props.models, () => {
  isLocked.value = false
  lockedModelName.value = '[ 未锁定 ]'
  isRotating = false

  nextTick(() => {
    createCards()
  })
}, { immediate: true })

onMounted(() => {
  nextTick(() => {
    initThreeScene()
    animate()

    // 初始化粒子 canvas
    if (particleCanvas.value && containerRef.value) {
      const rect = containerRef.value.getBoundingClientRect()
      particleCanvas.value.width = rect.width
      particleCanvas.value.height = rect.height
    }
  })

  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  stopGesture()

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }

  // 清理 Three.js 资源
  if (renderer) {
    renderer.dispose()
  }
  cards.forEach(card => {
    card.geometry.dispose()
    card.material.dispose()
  })

  // 清理背景粒子
  if (backgroundParticles) {
    backgroundParticles.geometry.dispose()
    backgroundParticles.material.dispose()
  }

  // 清理极光背景
  if (scene) {
    scene.traverse((obj) => {
      if (obj.userData && obj.userData.isAurora) {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) obj.material.dispose()
      }
    })
  }

  window.removeEventListener('resize', onResize)
})
</script>

<style lang="scss" scoped>
// 玻璃拟态配色
$glass-bg: rgba(255, 255, 255, 0.15);
$glass-border: rgba(255, 255, 255, 0.3);
$glass-shadow: 0 8px 32px rgba(31, 38, 135, 0.2);
$glass-blur: blur(12px);

$gradient-primary: linear-gradient(135deg, #FF6B6B 0%, #FFD93D 100%);
$color-primary: #FF6B6B;
$color-secondary: #FFD93D;
$color-text: #2d3748;
$color-text-light: #718096;

.three-carousel-selector {
  position: relative;
  min-height: 600px;
  background: $glass-bg;
  backdrop-filter: $glass-blur;
  -webkit-backdrop-filter: $glass-blur;
  border: 1px solid $glass-border;
  border-radius: 20px;
  overflow: hidden;
  user-select: none;
  box-shadow: $glass-shadow;
}

.three-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.particle-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}

.ui-layer {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 10;
  pointer-events: none;
}

.status-row {
  font-size: 14px;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}

.status-label {
  color: $color-text-light;
}

.status-value {
  color: $color-text;
  font-weight: 500;

  &.ready {
    color: $color-primary;
  }

  &.loading {
    color: $color-secondary;
  }

  &.highlight {
    background: $gradient-primary;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: bold;
    font-size: 18px;
  }
}

.gesture-instructions {
  position: absolute;
  bottom: 100px;
  left: 20px;
  color: $color-text-light;
  font-size: 13px;
  line-height: 2;
  border-left: 3px solid $color-primary;
  padding-left: 12px;
  z-index: 10;
  pointer-events: none;
}

.instruction-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.instruction-icon {
  font-size: 16px;
}

.empty-state,
.loading-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: center;
  align-items: center;
  color: $color-text;
  z-index: 10;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    color: $color-primary;
    animation: float 3s ease-in-out infinite;
  }

  p {
    font-size: 16px;
    margin-top: 8px;
    color: $color-text-light;
  }

  .empty-hint {
    font-size: 13px;
    color: $color-text-light;
    opacity: 0.7;
  }
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 107, 107, 0.2);
  border-top-color: $color-primary;
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

.control-bar {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 16px;
  z-index: 10;
}

.gesture-section {
  display: flex;
  align-items: center;
  gap: 12px;

  :deep(.el-switch) {
    --el-switch-on-color: #{$color-primary};
    --el-switch-off-color: rgba(255, 255, 255, 0.3);
  }

  :deep(.el-switch__label) {
    color: $color-text-light;
    font-size: 12px;
  }
}

.camera-preview {
  position: relative;
  width: 120px;
  height: 90px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid $glass-border;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

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
    border: 2px solid $color-primary;
    border-radius: 12px;
    pointer-events: none;
    opacity: 0.5;
  }
}

.confirm-btn {
  background: $gradient-primary !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600;
  border-radius: 25px !important;
  padding: 12px 28px !important;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(255, 107, 107, 0.5);
  }

  &:disabled {
    opacity: 0.5;
  }

  .locked-text {
    color: #fff;
  }
}
</style>
