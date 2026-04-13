<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <el-container>
        <!-- 侧边栏 -->
        <el-aside width="220px" class="sidebar">
          <div class="logo">
            <el-icon><Headset /></el-icon>
            <span>ASD 系统</span>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            class="glass-menu"
          >
            <el-menu-item index="/">
              <el-icon><HomeFilled /></el-icon>
              <span>首页</span>
            </el-menu-item>
            <el-menu-item index="/models">
              <el-icon><Files /></el-icon>
              <span>模型管理</span>
            </el-menu-item>
            <el-menu-item index="/data">
              <el-icon><Document /></el-icon>
              <span>数据管理</span>
            </el-menu-item>
            <el-menu-item index="/detection">
              <el-icon><Cpu /></el-icon>
              <span>异常检测</span>
            </el-menu-item>
            <el-menu-item index="/results">
              <el-icon><DataAnalysis /></el-icon>
              <span>检测历史</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <!-- 主内容区 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
// 玻璃拟态配色变量
$gradient-primary: linear-gradient(135deg, #FF6B6B 0%, #FFD93D 100%);
$color-primary: #FF6B6B;
$color-secondary: #FFD93D;
$color-text: #2d3748;
$color-text-light: #718096;
$glass-bg: rgba(255, 255, 255, 0.2);
$glass-border: rgba(255, 255, 255, 0.3);
$glass-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
$glass-blur: blur(12px);

.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.el-container {
  height: 100%;
}

.sidebar {
  background: $glass-bg;
  backdrop-filter: $glass-blur;
  -webkit-backdrop-filter: $glass-blur;
  border-right: 1px solid $glass-border;
  box-shadow: $glass-shadow;
  overflow-y: auto;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid $glass-border;
    background: $gradient-primary;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;

    .el-icon {
      font-size: 24px;
      margin-right: 8px;
      color: $color-primary;
      -webkit-text-fill-color: $color-primary;
    }
  }

  .glass-menu {
    background: transparent !important;
    border-right: none;

    :deep(.el-menu-item) {
      color: $color-text;
      border-radius: 12px;
      margin: 4px 8px;
      transition: all 0.3s ease;

      &:hover {
        background: rgba(255, 107, 107, 0.1) !important;
        color: $color-primary;
      }

      &.is-active {
        background: $gradient-primary !important;
        color: #fff !important;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);

        .el-icon {
          color: #fff !important;
        }
      }

      .el-icon {
        color: $color-text-light;
      }
    }
  }
}

.main-content {
  background: transparent;
  padding: 20px;
  overflow-y: auto;
}
</style>
