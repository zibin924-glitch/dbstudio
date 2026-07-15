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
      <el-header class="app-header" height="50px">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useConnectionStore } from '@/stores/connection.js'

const route = useRoute()
const connectionStore = useConnectionStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || 'DBStudio')
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
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
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

.app-main {
  flex: 1;
  overflow: auto;
  background: #f5f7fa;
  padding: 16px;
}
</style>
