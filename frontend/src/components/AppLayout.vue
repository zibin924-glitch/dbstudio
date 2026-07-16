<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="app-sidebar">
      <div class="sidebar-header">
        <el-icon :size="24" color="#409eff"><Coin /></el-icon>
        <span class="app-title">DBStudio</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        background-color="#1d1e1f"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/connections">
          <el-icon><Link /></el-icon>
          <span>Connections</span>
        </el-menu-item>
        <el-menu-item index="/explorer">
          <el-icon><FolderOpened /></el-icon>
          <span>Structure Explorer</span>
        </el-menu-item>
        <el-menu-item index="/query">
          <el-icon><EditPen /></el-icon>
          <span>SQL Console</span>
        </el-menu-item>
        <el-menu-item index="/generator">
          <el-icon><Document /></el-icon>
          <span>Generator</span>
        </el-menu-item>
        <el-menu-item index="/api-gateway">
          <el-icon><Share /></el-icon>
          <span>API Gateway</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <span class="version-text">v1.0.0</span>
      </div>
    </el-aside>
    <el-container class="main-container">
      <!-- H-F4: 后端不可达全局提示横幅 -->
      <el-alert
        v-if="!backendStatus.reachable"
        title="后端服务不可达，请检查服务是否正常运行"
        type="error"
        :closable="false"
        show-icon
        class="backend-unreachable-banner"
      />
      <el-header class="app-header" height="50px">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 暗色模式切换开关 -->
          <div class="dark-mode-toggle">
            <el-icon :size="16" class="theme-icon">
              <Sunny v-if="!isDark" />
              <Moon v-else />
            </el-icon>
            <el-switch
              v-model="isDark"
              :active-action-icon="MoonIcon"
              :inactive-action-icon="SunnyIcon"
              size="small"
              @change="toggleDarkMode"
            />
          </div>
          <el-tag type="success" size="small" v-if="connectionStore.currentConnection">
            {{ connectionStore.currentConnection.name }}
          </el-tag>
        </div>
      </el-header>
      <el-main class="app-main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, h, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useConnectionStore } from '@/stores/connection.js'
import { backendStatus } from '@/api/index.js'
import { Sunny, Moon } from '@element-plus/icons-vue'

const route = useRoute()
const connectionStore = useConnectionStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || 'DBStudio')

// 暗色模式状态（仅保存在内存中，不使用 localStorage）
const isDark = ref(false)

// 用于 el-switch 的图标组件
const SunnyIcon = h(Sunny)
const MoonIcon = h(Moon)

/** 切换暗色/亮色模式 */
function toggleDarkMode(val) {
  const html = document.documentElement
  if (val) {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}

// 组件挂载时检查系统偏好
onMounted(() => {
  // 可选：根据系统偏好初始化为暗色模式（但状态仅保存于内存）
  // 这里默认亮色模式
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
}
.app-sidebar {
  background-color: #1d1e1f;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid #363636;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 50px;
  padding: 0 20px;
  border-bottom: 1px solid #363636;
}
.app-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 1px;
}
.sidebar-menu {
  flex: 1;
  border-right: none;
  padding-top: 8px;
}
.sidebar-menu .el-menu-item {
  margin: 2px 8px;
  border-radius: 6px;
  height: 44px;
  line-height: 44px;
}
.sidebar-menu .el-menu-item:hover {
  background-color: #333436 !important;
}
.sidebar-menu .el-menu-item.is-active {
  background-color: rgba(64, 158, 255, 0.15) !important;
}
.sidebar-footer {
  padding: 12px 20px;
  border-top: 1px solid #363636;
  text-align: center;
}
.version-text {
  font-size: 12px;
  color: #666;
}
.main-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--header-bg, #fff);
  border-bottom: 1px solid var(--header-border, #e4e7ed);
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: background 0.3s, border-color 0.3s;
}
.header-left {
  display: flex;
  align-items: center;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 暗色模式切换区域 */
.dark-mode-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
}
.theme-icon {
  color: var(--header-text, #606266);
  transition: color 0.3s;
}

.app-main {
  flex: 1;
  overflow: auto;
  background: var(--main-bg, #f5f7fa);
  padding: 16px;
  transition: background 0.3s;
}

/* ====== 暗色模式样式变量 ====== */
:global(html.dark) .app-header {
  --header-bg: #1d1e1f;
  --header-border: #363636;
  --header-text: #cfd3dc;
}
:global(html.dark) .app-main {
  --main-bg: #0a0a0a;
}

/* 暗色模式下全局组件样式覆盖 */
:global(html.dark) .app-main :deep(.el-table) {
  --el-table-bg-color: #1d1e1f;
  --el-table-tr-bg-color: #1d1e1f;
  --el-table-header-bg-color: #262727;
  --el-table-row-hover-bg-color: #262727;
  --el-table-border-color: #363636;
  --el-table-text-color: #cfd3dc;
  --el-table-header-text-color: #e5eaf3;
}
:global(html.dark) .app-main :deep(.el-descriptions) {
  --el-descriptions-table-border: #363636;
  --el-descriptions-item-bordered-label-background: #262727;
}
:global(html.dark) .app-main :deep(.el-card) {
  --el-card-bg-color: #1d1e1f;
  --el-card-border-color: #363636;
}

/* H-F4: 后端不可达横幅样式 */
.backend-unreachable-banner {
  flex-shrink: 0;
  border-radius: 0;
  border-left: none;
  border-right: none;
}
.backend-unreachable-banner :deep(.el-alert__title) {
  font-size: 13px;
  font-weight: 500;
}
</style>
