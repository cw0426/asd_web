/**
 * 手势检测模块 - 基于 MediaPipe Hands
 * 支持手势：握拳、张开手掌、左右滑动
 */

export class GestureDetector {
  constructor() {
    this.hands = null
    this.camera = null
    this.videoElement = null
    this.canvasElement = null
    this.ctx = null
    this.running = false
    this.gestureCallback = null
    this.landmarkCallback = null

    // 手势状态追踪
    this._prevWristX = null
    this._swipeStartX = null
    this._swipeStartTime = null
    this._lastGesture = 'idle'
    this._gestureHoldStart = 0
    this._gestureDebounce = 300 // ms

    // MediaPipe 关键点索引
    // WRIST = 0
    // THUMB_TIP = 4, INDEX_TIP = 8, MIDDLE_TIP = 12, RING_TIP = 16, PINKY_TIP = 20
    // INDEX_MCP = 5, MIDDLE_MCP = 9, RING_MCP = 13, PINKY_MCP = 17
  }

  /**
   * 初始化并启动手势检测
   * @param {HTMLVideoElement} videoEl - 视频元素
   * @param {HTMLCanvasElement} canvasEl - 绘制手部关键点的 Canvas
   */
  async start(videoEl, canvasEl) {
    this.videoElement = videoEl
    this.canvasElement = canvasEl
    this.ctx = canvasEl.getContext('2d')

    try {
      // 动态导入 MediaPipe
      const { Hands } = await import('@mediapipe/hands')
      const { Camera } = await import('@mediapipe/camera_utils')

      this.hands = new Hands({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
        }
      })

      this.hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
      })

      this.hands.onResults((results) => this._onResults(results))

      // 启动摄像头
      this.camera = new Camera(videoEl, {
        onFrame: async () => {
          if (this.running && this.hands) {
            await this.hands.send({ image: videoEl })
          }
        },
        width: 320,
        height: 240
      })

      await this.camera.start()
      this.running = true
      return true
    } catch (error) {
      console.warn('手势检测初始化失败，将使用降级方案:', error.message)
      return false
    }
  }

  stop() {
    this.running = false
    if (this.camera) {
      this.camera.stop()
      this.camera = null
    }
    if (this.hands) {
      this.hands.close()
      this.hands = null
    }
    // 停止摄像头流
    if (this.videoElement && this.videoElement.srcObject) {
      const tracks = this.videoElement.srcObject.getTracks()
      tracks.forEach(track => track.stop())
      this.videoElement.srcObject = null
    }
  }

  /**
   * 注册手势回调
   * @param {Function} callback - 回调函数，参数: { type, position, confidence }
   *   type: 'swipe_left' | 'swipe_right' | 'fist' | 'open' | 'idle'
   *   position: { x, y } - 手掌中心位置（归一化 0~1）
   *   confidence: 0~1
   */
  onGesture(callback) {
    this.gestureCallback = callback
  }

  /**
   * 注册关键点回调（用于粒子跟随等）
   * @param {Function} callback - 回调函数，参数: landmarks[]
   */
  onLandmarks(callback) {
    this.landmarkCallback = callback
  }

  _onResults(results) {
    // 绘制手部关键点
    this._drawLandmarks(results)

    if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
      this._emitGesture('idle', { x: 0.5, y: 0.5 }, 0)
      this._prevWristX = null
      this._swipeStartX = null
      return
    }

    const landmarks = results.multiHandLandmarks[0]
    const wrist = landmarks[0]

    // 回调关键点数据
    if (this.landmarkCallback) {
      this.landmarkCallback(landmarks)
    }

    // 检测手势
    const gesture = this._classifyGesture(landmarks)
    const palmCenter = {
      x: (landmarks[0].x + landmarks[9].x) / 2,
      y: (landmarks[0].y + landmarks[9].y) / 2
    }

    // 滑动检测
    if (gesture === 'open') {
      if (this._swipeStartX === null) {
        this._swipeStartX = wrist.x
        this._swipeStartTime = Date.now()
      } else {
        const dx = wrist.x - this._swipeStartX
        const dt = Date.now() - this._swipeStartTime
        if (dt > 200 && dt < 1500) {
          if (dx > 0.2) {
            // 注意：摄像头画面是镜像的，向右滑动在画面中手腕x增大
            this._emitGesture('swipe_right', palmCenter, Math.min(dx / 0.4, 1))
            this._swipeStartX = null
            return
          } else if (dx < -0.2) {
            this._emitGesture('swipe_left', palmCenter, Math.min(Math.abs(dx) / 0.4, 1))
            this._swipeStartX = null
            return
          }
        }
      }
    } else {
      this._swipeStartX = null
    }

    // 握拳检测（带防抖）
    if (gesture === this._lastGesture) {
      // 同一手势持续
    } else {
      this._gestureHoldStart = Date.now()
      this._lastGesture = gesture
    }

    if (gesture === 'fist' && Date.now() - this._gestureHoldStart > this._gestureDebounce) {
      this._emitGesture('fist', palmCenter, 0.9)
    } else if (gesture === 'open') {
      this._emitGesture('open', palmCenter, 0.8)
    } else {
      this._emitGesture('idle', palmCenter, 0.5)
    }

    this._prevWristX = wrist.x
  }

  /**
   * 分类手势
   * @param {Array} landmarks - 21个手部关键点
   * @returns {string} 'fist' | 'open' | 'point' | 'idle'
   */
  _classifyGesture(landmarks) {
    const wrist = landmarks[0]

    // 计算手掌大小（用于归一化距离）
    const middleMcp = landmarks[9]
    const palmSize = Math.sqrt(
      (middleMcp.x - wrist.x) ** 2 + (middleMcp.y - wrist.y) ** 2
    )

    if (palmSize < 0.01) return 'idle'

    // 各指尖到掌心的距离，归一化
    const fingerTips = [landmarks[8], landmarks[12], landmarks[16], landmarks[20]] // 食指、中指、无名指、小指
    const fingerMcps = [landmarks[5], landmarks[9], landmarks[13], landmarks[17]]

    let extendedCount = 0
    for (let i = 0; i < 4; i++) {
      const tipDist = Math.sqrt(
        (fingerTips[i].x - wrist.x) ** 2 + (fingerTips[i].y - wrist.y) ** 2
      )
      const mcpDist = Math.sqrt(
        (fingerMcps[i].x - wrist.x) ** 2 + (fingerMcps[i].y - wrist.y) ** 2
      )
      // 指尖到掌心距离 > MCP到掌心距离的1.2倍 = 手指伸展
      if (tipDist > mcpDist * 1.2) {
        extendedCount++
      }
    }

    // 拇指检测
    const thumbTip = landmarks[4]
    const thumbMcp = landmarks[2]
    const thumbExt = Math.sqrt(
      (thumbTip.x - wrist.x) ** 2 + (thumbTip.y - wrist.y) ** 2
    ) / palmSize
    if (thumbExt > 1.5) extendedCount++

    if (extendedCount <= 1) return 'fist'
    if (extendedCount >= 4) return 'open'
    if (extendedCount === 1) return 'point'
    return 'idle'
  }

  _emitGesture(type, position, confidence) {
    if (this.gestureCallback) {
      this.gestureCallback({ type, position, confidence })
    }
  }

  _drawLandmarks(results) {
    if (!this.ctx || !this.canvasElement) return

    this.canvasElement.width = this.canvasElement.clientWidth
    this.canvasElement.height = this.canvasElement.clientHeight
    this.ctx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height)

    if (!results.multiHandLandmarks) return

    for (const landmarks of results.multiHandLandmarks) {
      // 绘制连线
      const connections = [
        [0, 1], [1, 2], [2, 3], [3, 4],     // 拇指
        [0, 5], [5, 6], [6, 7], [7, 8],     // 食指
        [0, 9], [9, 10], [10, 11], [11, 12], // 中指
        [0, 13], [13, 14], [14, 15], [15, 16], // 无名指
        [0, 17], [17, 18], [18, 19], [19, 20], // 小指
        [5, 9], [9, 13], [13, 17]             // 掌心连线
      ]

      const w = this.canvasElement.width
      const h = this.canvasElement.height

      this.ctx.strokeStyle = '#00ffff'
      this.ctx.lineWidth = 2
      for (const [a, b] of connections) {
        this.ctx.beginPath()
        this.ctx.moveTo(landmarks[a].x * w, landmarks[a].y * h)
        this.ctx.lineTo(landmarks[b].x * w, landmarks[b].y * h)
        this.ctx.stroke()
      }

      // 绘制关键点
      for (const lm of landmarks) {
        this.ctx.beginPath()
        this.ctx.arc(lm.x * w, lm.y * h, 3, 0, Math.PI * 2)
        this.ctx.fillStyle = '#00ffff'
        this.ctx.fill()
      }
    }
  }
}
