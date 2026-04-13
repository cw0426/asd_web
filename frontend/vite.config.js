import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler'
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 大文件上传需要更长的超时
        timeout: 600000, // 10分钟
        proxyTimeout: 600000,
        // 配置 http-proxy 选项
        configure: (proxy, options) => {
          // 不限制请求体大小，允许大文件上传
        }
      }
    }
  }
})
