/**
 * 2D 粒子引擎 - 用于全息投影风格的视觉效果
 * 支持粒子环绕、聚拢、散开、爆发、拖尾等行为
 */

class Particle {
  constructor(x, y, config = {}) {
    this.x = x
    this.y = y
    this.vx = config.vx || (Math.random() - 0.5) * 2
    this.vy = config.vy || (Math.random() - 0.5) * 2
    this.size = config.size || Math.random() * 3 + 1
    this.color = config.color || '#00ffff'
    this.alpha = config.alpha || 1
    this.life = config.life || 1
    this.maxLife = this.life
    this.decay = config.decay || 0.005
    this.trail = []
    this.trailLength = config.trailLength || 8
    this.friction = config.friction || 0.98
    this.gravity = config.gravity || 0
  }

  update() {
    // 记录轨迹
    this.trail.push({ x: this.x, y: this.y, alpha: this.alpha })
    if (this.trail.length > this.trailLength) {
      this.trail.shift()
    }

    this.vx *= this.friction
    this.vy *= this.friction
    this.vy += this.gravity
    this.x += this.vx
    this.y += this.vy
    this.life -= this.decay
    this.alpha = Math.max(0, this.life / this.maxLife)
  }

  draw(ctx) {
    // 绘制拖尾
    if (this.trail.length > 1) {
      ctx.beginPath()
      ctx.moveTo(this.trail[0].x, this.trail[0].y)
      for (let i = 1; i < this.trail.length; i++) {
        ctx.lineTo(this.trail[i].x, this.trail[i].y)
      }
      ctx.strokeStyle = this.color
      ctx.globalAlpha = this.alpha * 0.3
      ctx.lineWidth = this.size * 0.5
      ctx.stroke()
    }

    // 绘制粒子本体
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = this.alpha
    ctx.fill()

    // 光晕效果
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size * 2, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = this.alpha * 0.15
    ctx.fill()

    ctx.globalAlpha = 1
  }

  get isDead() {
    return this.life <= 0
  }
}

export class ParticleEngine {
  constructor(canvas) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    this.particles = []
    this.maxParticles = 300
    this.animating = false
    this._animFrameId = null
    this._lastTime = 0
    this._behavior = 'idle' // idle | orbit | gather | scatter | burst | trail
    this._behaviorTarget = null
    this._orbitAngle = 0
  }

  resize(width, height) {
    this.canvas.width = width
    this.canvas.height = height
  }

  // 发射粒子
  emit(x, y, count = 1, config = {}) {
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = config.angle ?? Math.random() * Math.PI * 2
      const speed = config.speed ?? (Math.random() * 2 + 0.5)
      this.particles.push(new Particle(x, y, {
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        color: config.color || '#00ffff',
        size: config.size || Math.random() * 3 + 1,
        life: config.life || 1,
        decay: config.decay || 0.005,
        trailLength: config.trailLength || 8,
        friction: config.friction || 0.98,
        ...config
      }))
    }
  }

  // 环绕模式 - 粒子围绕中心旋转
  startOrbit(centerX, centerY, radius) {
    this._behavior = 'orbit'
    this._behaviorTarget = { centerX, centerY, radius }
    // 清除现有粒子，生成环绕粒子
    this.particles = []
    const count = 60
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 / count) * i
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius
      this.particles.push(new Particle(x, y, {
        color: '#00ffff',
        size: Math.random() * 2.5 + 0.5,
        life: 999,
        decay: 0,
        trailLength: 12,
        friction: 1,
        _orbitAngle: angle,
        _orbitSpeed: 0.008 + Math.random() * 0.004,
        _orbitRadius: radius + (Math.random() - 0.5) * 30,
        _orbitCenterX: centerX,
        _orbitCenterY: centerY
      }))
    }
  }

  // 更新环绕粒子
  _updateOrbit() {
    for (const p of this.particles) {
      if (p._orbitAngle !== undefined) {
        p._orbitAngle += p._orbitSpeed
        p.x = p._orbitCenterX + Math.cos(p._orbitAngle) * p._orbitRadius
        p.y = p._orbitCenterY + Math.sin(p._orbitAngle) * p._orbitRadius
        p.trail.push({ x: p.x, y: p.y, alpha: p.alpha })
        if (p.trail.length > p.trailLength) p.trail.shift()
      }
    }
  }

  // 聚拢 - 粒子向目标聚集
  gather(targetX, targetY, count = 50) {
    this._behavior = 'gather'
    this._behaviorTarget = { targetX, targetY }
    // 发射从四周向中心聚集的粒子
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = Math.random() * Math.PI * 2
      const dist = 200 + Math.random() * 150
      const x = targetX + Math.cos(angle) * dist
      const y = targetY + Math.sin(angle) * dist
      const dx = targetX - x
      const dy = targetY - y
      const len = Math.sqrt(dx * dx + dy * dy)
      const speed = 3 + Math.random() * 2
      this.particles.push(new Particle(x, y, {
        vx: (dx / len) * speed,
        vy: (dy / len) * speed,
        color: '#ffd700',
        size: Math.random() * 3 + 1,
        life: 1,
        decay: 0.008,
        trailLength: 15,
        friction: 0.99
      }))
    }
  }

  // 爆发 - 粒子从中心高速扩散
  burst(centerX, centerY, count = 80) {
    this._behavior = 'burst'
    // 先清除环绕粒子
    this.particles = this.particles.filter(p => p._orbitAngle === undefined)

    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = Math.random() * Math.PI * 2
      const speed = 3 + Math.random() * 6
      this.particles.push(new Particle(centerX, centerY, {
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        color: Math.random() > 0.5 ? '#ffffff' : '#00ffff',
        size: Math.random() * 4 + 1,
        life: 1,
        decay: 0.015,
        trailLength: 20,
        friction: 0.96
      }))
    }
  }

  // 拖尾效果 - 从一个位置滑动到另一个位置
  trail(fromX, fromY, toX, toY, count = 30) {
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const t = Math.random()
      const x = fromX + (toX - fromX) * t + (Math.random() - 0.5) * 40
      const y = fromY + (toY - fromY) * t + (Math.random() - 0.5) * 40
      const dx = toX - fromX
      const dy = toY - fromY
      const len = Math.sqrt(dx * dx + dy * dy) || 1
      const speed = 1 + Math.random()
      this.particles.push(new Particle(x, y, {
        vx: (dx / len) * speed,
        vy: (dy / len) * speed,
        color: '#00ffff',
        size: Math.random() * 2 + 0.5,
        life: 0.8,
        decay: 0.02,
        trailLength: 10,
        friction: 0.97
      }))
    }
  }

  // 跟随指尖
  followFinger(x, y, count = 3) {
    this.emit(x, y, count, {
      color: '#00ffff',
      speed: 0.5,
      size: Math.random() * 2 + 1,
      life: 0.6,
      decay: 0.03,
      trailLength: 10
    })
  }

  // 更新所有粒子
  update() {
    if (this._behavior === 'orbit') {
      this._updateOrbit()
    }

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i]
      // 环绕粒子不调用常规 update
      if (p._orbitAngle !== undefined) continue
      p.update()
      if (p.isDead) {
        this.particles.splice(i, 1)
      }
    }
  }

  // 渲染
  render() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
    for (const p of this.particles) {
      p.draw(this.ctx)
    }
  }

  // 动画循环
  start() {
    if (this.animating) return
    this.animating = true
    this._lastTime = performance.now()
    const loop = (time) => {
      if (!this.animating) return
      this.update()
      this.render()
      this._animFrameId = requestAnimationFrame(loop)
    }
    this._animFrameId = requestAnimationFrame(loop)
  }

  stop() {
    this.animating = false
    if (this._animFrameId) {
      cancelAnimationFrame(this._animFrameId)
      this._animFrameId = null
    }
  }

  clear() {
    this.particles = []
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
    this._behavior = 'idle'
  }

  // 更新环绕中心（用于卡片切换时粒子跟随）
  updateOrbitCenter(centerX, centerY) {
    for (const p of this.particles) {
      if (p._orbitAngle !== undefined) {
        p._orbitCenterX = centerX
        p._orbitCenterY = centerY
      }
    }
    if (this._behaviorTarget) {
      this._behaviorTarget.centerX = centerX
      this._behaviorTarget.centerY = centerY
    }
  }
}
