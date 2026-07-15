<template>
  <div class="query-console-page">
    <!-- Top Bar -->
    <div class="console-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedConnectionId"
          placeholder="Select connection"
          filterable
          size="default"
          style="width: 260px;"
        >
          <el-option
            v-for="conn in connectionStore.connections"
            :key="conn.id"
            :label="`${conn.name} (${conn.db_type})`"
            :value="conn.id"
          />
        </el-select>
        <el-switch
          v-model="readOnlyMode"
          active-text="Read-only"
          inactive-text=""
          size="small"
          style="margin-left: 12px;"
        />
      </div>
      <div class="toolbar-right">
        <el-button
          :type="showHistory ? 'primary' : 'default'"
          plain
          size="default"
          @click="showHistory = !showHistory"
        >
          <el-icon><Clock /></el-icon>
          History
        </el-button>
      </div>
    </div>

    <!-- Tab Bar -->
    <div class="tab-bar">
      <el-tabs
        v-model="activeTabId"
        type="card"
        closable
        @tab-remove="handleTabRemove"
        @tab-click="handleTabClick"
        class="query-tabs"
      >
        <el-tab-pane
          v-for="tab in queryStore.tabs"
          :key="tab.id"
          :label="tab.name"
          :name="String(tab.id)"
        />
      </el-tabs>
      <el-button class="add-tab-btn" text size="small" @click="handleAddTab">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <!-- Main Content Area -->
    <div class="console-content">
      <div class="editor-area">
        <!-- SQL Editor -->
        <div class="editor-section">
          <SqlEditor
            v-model="currentSql"
            :read-only="readOnlyMode"
            @execute="handleExecute"
          />
        </div>

        <!-- Splitter -->
        <div class="horizontal-splitter"></div>

        <!-- Query Results -->
        <div class="results-section" v-loading="currentTab?.loading">
          <QueryResult
            :columns="currentTab?.columns || []"
            :rows="currentTab?.rows || []"
            :total="currentTab?.total || 0"
            :page="currentTab?.page || 1"
            :page-size="currentTab?.pageSize || 50"
            :duration-ms="currentTab?.durationMs"
            :error="currentTab?.error"
            @export="handleExport"
            @page-change="handlePageChange"
          />
        </div>
      </div>

      <!-- History Drawer -->
      <transition name="slide-right">
        <div class="history-drawer" v-if="showHistory">
          <QueryHistory
            :connection-id="selectedConnectionId"
            @select="handleHistorySelect"
          />
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import { useQueryStore } from '@/stores/query.js'
import SqlEditor from '@/components/SqlEditor.vue'
import QueryResult from '@/components/QueryResult.vue'
import QueryHistory from '@/components/QueryHistory.vue'

const connectionStore = useConnectionStore()
const queryStore = useQueryStore()

const selectedConnectionId = ref(null)
const readOnlyMode = ref(false)
const showHistory = ref(false)

const activeTabId = computed({
  get: () => String(queryStore.activeTabId),
  set: (val) => queryStore.setActiveTab(Number(val))
})

const currentTab = computed(() => queryStore.activeTab)

const currentSql = computed({
  get: () => currentTab.value?.sql || '',
  set: (val) => {
    if (currentTab.value) {
      currentTab.value.sql = val
    }
  }
})

onMounted(() => {
  connectionStore.fetchConnections().then(() => {
    if (connectionStore.currentConnection) {
      selectedConnectionId.value = connectionStore.currentConnection.id
    } else if (connectionStore.connections.length > 0) {
      selectedConnectionId.value = connectionStore.connections[0].id
    }
  })
})

function handleAddTab() {
  queryStore.addTab()
}

function handleTabRemove(tabId) {
  queryStore.removeTab(Number(tabId))
}

function handleTabClick(tab) {
  queryStore.setActiveTab(Number(tab.paneName))
}

async function handleExecute(sql) {
  if (!selectedConnectionId.value) {
    ElMessage.warning('Please select a connection first')
    return
  }
  if (!sql || !sql.trim()) {
    ElMessage.warning('Please enter a SQL query')
    return
  }

  try {
    await queryStore.executeQuery(selectedConnectionId.value, sql)
  } catch (error) {
    // Error is already set in the tab state
  }
}

async function handlePageChange(page) {
  if (!selectedConnectionId.value || !currentTab.value?.sql) return
  try {
    await queryStore.executeQuery(
      selectedConnectionId.value,
      currentTab.value.sql,
      page,
      currentTab.value.pageSize
    )
  } catch (error) {
    // Error handled in store
  }
}

async function handleExport(format) {
  if (!selectedConnectionId.value || !currentTab.value?.sql) return

  try {
    // Client-side CSV/JSON export is handled by QueryResult component
    if (format === 'excel') {
      const response = await queryStore.exportResults(
        selectedConnectionId.value,
        currentTab.value.sql,
        format
      )
      // Download the blob
      if (response instanceof Blob) {
        const url = URL.createObjectURL(response)
        const a = document.createElement('a')
        a.href = url
        a.download = `query_result.${format === 'excel' ? 'xlsx' : format}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
      ElMessage.success('Export complete')
    } else {
      ElMessage.success(`${format.toUpperCase()} exported`)
    }
  } catch (error) {
    ElMessage.error('Export failed')
  }
}

function handleHistorySelect(sql) {
  if (currentTab.value) {
    currentTab.value.sql = sql
  }
}
</script>

<style scoped>
.query-console-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 98px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.console-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-bar {
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
}

.query-tabs {
  flex: 1;
}

.query-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.query-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.add-tab-btn {
  margin-left: 4px;
  flex-shrink: 0;
}

.console-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.editor-section {
  height: 45%;
  min-height: 150px;
}

.horizontal-splitter {
  height: 3px;
  background: #e4e7ed;
  flex-shrink: 0;
}

.results-section {
  flex: 1;
  overflow: auto;
}

.history-drawer {
  width: 320px;
  border-left: 1px solid #e4e7ed;
  background: #fff;
  overflow: hidden;
  flex-shrink: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  width: 0;
  opacity: 0;
}
</style>
