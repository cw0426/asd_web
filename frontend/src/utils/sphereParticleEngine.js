/**
 * 3D 球体粒子引擎 - 用于全息投影风格的视觉效果
 * 支持粒子环绕、旋转拖尾、爆发、脉冲等行为
 */

class Particle3D {
  constructor(x, y, z, config = {}) {
    this.x = x
    this.y = y
    this.z = z
    this.vx = config.vx || (Math.random() - 0.5) * 2
    this.vy = config.vy || (Math.random() - 0.5) * 2
    this.vz = config.vz || (Math.random() - 0.5) * 2
    this.size = config.size || Math.random() * 3 + 1
    this.color = config.color || '#00ffff'
    this.alpha = config.alpha || 1
    this.life = config.life || 1
    this.maxLife = this.life
    this.decay = config.decay || 0.005
    this.trail = []
    this.trailLength = config.trailLength || 12
    this.friction = config.friction || 0.98
    this.gravity = config.gravity || 0

    // 3D 环绕参数
    this.orbitAngleX = config.orbitAngleX
    this.orbitAngleY = config.orbitAngleY
    this.orbitRadius = config.orbitRadius
    this.orbitSpeedX = config.orbitSpeedX || 0
    this.orbitSpeedY = config.orbitSpeedY || 0
  }

  update(centerX, centerY, centerZ = 0) {
    // 3D 环绕模式
    if (this.orbitAngleX !== undefined && this.orbitAngleY !== undefined) {
      this.orbitAngleX += this.orbitSpeedX
      this.orbitAngleY += this.orbitSpeedY

      // 球面坐标转换
      this.x = centerX + this.orbitRadius * Math.sin(this.orbitAngleX) * Math.cos(this.orbitAngleY)
      this.y = centerY + this.orbitRadius * Math.sin(this.orbitAngleY)
      this.z = centerZ + this.orbitRadius * Math.cos(this.orbitAngleX) * Math.cos(this.orbitAngleY)

      // 记录轨迹
      this.trail.push({ x: this.x, y: this.y, z: this.z, alpha: this.alpha })
      if (this.trail.length > this.trailLength) {
        this.trail.shift()
      }
      return
    }

    // 常规粒子更新
    this.trail.push({ x: this.x, y: this.y, z: this.z, alpha: this.alpha })
    if (this.trail.length > this.trailLength) {
      this.trail.shift()
    }

    this.vx *= this.friction
    this.vy *= this.friction
    this.vz *= this.friction
    this.vy += this.gravity
    this.x += this.vx
    this.y += this.vy
    this.z += this.vz
    this.life -= this.decay
    this.alpha = Math.max(0, this.life / this.maxLife)
  }

  draw(ctx, cameraX, cameraY, cameraZ) {
    // 3D 到 2D 投影
    const perspective = 800
    const scale = perspective / (perspective + this.z)

    const screenX = this.x * scale
    const screenY = this.y * scale
    const screenSize = this.size * scale

    // 绘制拖尾
    if (this.trail.length > 1) {
      ctx.beginPath()
      for (let i = 0; i < this.trail.length; i++) {
        const t = this.trail[i]
        const tScale = perspective / (perspective + t.z)
        const tx = t.x * tScale
        const ty = t.y * tScale
        if (i === 0) {
          ctx.moveTo(tx, ty)
        } else {
          ctx.lineTo(tx, ty)
        }
      }
      ctx.strokeStyle = this.color
      ctx.globalAlpha = this.alpha * 0.3
      ctx.lineWidth = screenSize * 0.5
      ctx.stroke()
    }

    // 绘制粒子本体
    ctx.beginPath()
    ctx.arc(screenX, screenY, screenSize, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = this.alpha
    ctx.fill()

    // 光晕效果
    ctx.beginPath()
    ctx.arc(screenX, screenY, screenSize * 2.5, 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = this.alpha * 0.15
    ctx.fill()

    ctx.globalAlpha = 1
  }

  get isDead() {
    return this.life <= 0 && this.orbitAngleX === undefined
  }
}

export class SphereParticleEngine {
  constructor(canvas) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    this.particles = []
    this.maxParticles = 400
    this.animating = false
    this._animFrameId = null

    // 相机位置
    this.cameraX = 0
    this.cameraY = 0
    this.cameraZ = 0

    // 球体中心
    this.centerX = 0
    this.centerY = 0

    // 旋转粒子参数
    this.rotateParticles = []
    this.rotateDirection = 0
  }

  resize(width, height) {
    this.canvas.width = width
    this.canvas.height = height
    this.centerX = width / 2
    this.centerY = height / 2
  }

  // 初始化环绕粒子
  initOrbitParticles(radius) {
    this.particles = []
    const count = 80

    for (let i = 0; i < count; i++) {
      const angleX = Math.random() * Math.PI * 2
      const angleY = Math.random() * Math.PI - Math.PI / 2
      const r = radius + (Math.random() - 0.5) * 60

      this.particles.push(new Particle3D(0, 0, 0, {
        orbitAngleX: angleX,
        orbitAngleY: angleY,
        orbitRadius: r,
        orbitSpeedX: 0.003 + Math.random() * 0.005,
        orbitSpeedY: 0.001 + Math.random() * 0.002,
        color: `hsl(${180 + Math.random() * 30}, 100%, 70%)`,
        size: Math.random() * 2 + 0.5,
        life: 999,
        decay: 0,
        trailLength: 15
      }))
    }
  }

  // 发射粒子
  emit(x, y, z, count = 1, config = {}) {
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = config.angle ?? Math.random() * Math.PI * 2
      const angleZ = config.angleZ ?? (Math.random() - 0.5) * Math.PI
      const speed = config.speed ?? (Math.random() * 3 + 1)

      this.particles.push(new Particle3D(x, y, z, {
        vx: Math.cos(angle) * Math.cos(angleZ) * speed,
        vy: Math.sin(angleZ) * speed,
        vz: Math.sin(angle) * Math.cos(angleZ) * speed,
        color: config.color || '#00ffff',
        size: config.size || Math.random() * 3 + 1,
        life: config.life || 1,
        decay: config.decay || 0.008,
        trailLength: config.trailLength || 12,
        friction: config.friction || 0.97,
        ...config
      }))
    }
  }

  // 爆发效果
  burst(x, y, count = 100) {
    // 清除环绕粒子
    this.particles = this.particles.filter(p => p.orbitAngleX !== undefined)

    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = Math.random() * Math.PI * 2
      const angleZ = (Math.random() - 0.5) * Math.PI
      const speed = 4 + Math.random() * 8

      this.particles.push(new Particle3D(x, y, 0, {
        vx: Math.cos(angle) * Math.cos(angleZ) * speed,
        vy: Math.sin(angleZ) * speed,
        vz: Math.sin(angle) * Math.cos(angleZ) * speed,
        color: Math.random() > 0.3 ? '#00ffff' : '#ffffff',
        size: Math.random() * 4 + 1,
        life: 1,
        decay: 0.012,
        trailLength: 25,
        friction: 0.95
      }))
    }
  }

  // 旋转粒子效果（啄木鸟手势时）
  emitRotateParticles(direction) {
    const count = 5
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = Math.random() * Math.PI * 2
      const radius = 200 + Math.random() * 100
      const x = this.centerX + Math.cos(angle) * radius
      const y = this.centerY + (Math.random() - 0.5) * 200
      const z = Math.sin(angle) * radius

      this.particles.push(new Particle3D(x - this.centerX, y - this.centerY, z, {
        vx: direction * (2 + Math.random() * 2),
        vy: (Math.random() - 0.5) * 2,
        vz: (Math.random() - 0.5) * 2,
        color: '#4fc3f7',
        size: Math.random() * 2 + 1,
        life: 0.8,
        decay: 0.02,
        trailLength: 18,
        friction: 0.96
      }))
    }
  }

  // 脉冲效果（张开手掌时）
  pulse() {
    const count = 30
    for (let i = 0; i < count; i++) {
      if (this.particles.length >= this.maxParticles) break
      const angle = Math.random() * Math.PI * 2
      const angleZ = (Math.random() - 0.5) * Math.PI

      this.particles.push(new Particle3D(0, 0, 0, {
        vx: Math.cos(angle) * Math.cos(angleZ) * 3,
        vy: Math.sin(angleZ) * 3,
        vz: Math.sin(angle) * Math.cos(angleZ) * 3,
        color: '#00ffff',
        size: Math.random() * 3 + 1,
        life: 0.6,
        decay: 0.015,
        trailLength: 10,
        friction: 0.98
      }))
    }
  }

  // 跟随手掌
  followHand(normX, normY) {
    const x = (1 - normX) * this.canvas.width - this.centerX
    const y = normY * this.canvas.height - this.centerY

    this.emit(x, y, 0, 2, {
      color: '#00ffff',
      speed: 0.5,
      size: Math.random() * 2 + 1,
      life: 0.5,
      decay: 0.025,
      trailLength: 8
    })
  }

  // 更新所有粒子
  update() {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i]
      p.update(this.centerX, this.centerY, 0)
      if (p.isDead) {
        this.particles.splice(i, 1)
      }
    }
  }

  // 渲染
  render() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)

    // 按 z 坐标排序（远的先画）
    this.particles.sort((a, b) => b.z - a.z)

    for (const p of this.particles) {
      p.draw(this.ctx, this.cameraX, this.cameraY, this.cameraZ)
    }
  }

  // 动画循环
  start() {
    if (this.animating) return
    this.animating = true

    // 初始化环绕粒子
    this.initOrbitParticles(250)

    const loop = () => {
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
  }
}
