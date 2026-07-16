<template>
  <div class="query-console-page">
    <!-- 顶部工具栏 -->
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

    <!-- 标签栏 -->
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

    <!-- 主内容区 -->
    <div class="console-content">
      <div class="editor-area">
        <!-- SQL 编辑器 -->
        <div class="editor-section">
          <SqlEditor
            v-model="currentSql"
            :read-only="readOnlyMode"
            @execute="handleExecute"
          />
          <!-- EXPLAIN 按钮组（放在编辑器底部） -->
          <div class="explain-btn-bar">
            <el-button size="small" plain type="warning" @click="handleExplain(false)" :loading="explainLoading">
              <el-icon><TrendCharts /></el-icon>
              EXPLAIN
            </el-button>
            <el-button size="small" plain type="danger" @click="handleExplain(true)" :loading="explainLoading">
              EXPLAIN ANALYZE
            </el-button>
          </div>
        </div>

        <!-- 分隔条 -->
        <div class="horizontal-splitter"></div>

        <!-- 查询结果 / EXPLAIN 计划 -->
        <div class="results-section" v-loading="currentTab?.loading">
          <!-- EXPLAIN 面板 -->
          <template v-if="showExplainPlan">
            <div class="explain-panel">
              <div class="explain-panel-header">
                <span class="explain-panel-title">执行计划分析</span>
                <el-button size="small" text @click="showExplainPlan = false">
                  <el-icon><Close /></el-icon>
                  关闭
                </el-button>
              </div>
              <div class="explain-panel-body">
                <ExplainPlan
                  :connection-id="selectedConnectionId"
                  :sql="currentSql"
                  :db-type="currentDbType"
                  :analyze="explainAnalyze"
                />
              </div>
            </div>
          </template>

          <!-- 正常查询结果 -->
          <template v-else>
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
          </template>
        </div>
      </div>

      <!-- 历史记录抽屉 -->
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import { useQueryStore } from '@/stores/query.js'
import SqlEditor from '@/components/SqlEditor.vue'
import QueryResult from '@/components/QueryResult.vue'
import QueryHistory from '@/components/QueryHistory.vue'
import ExplainPlan from '@/components/ExplainPlan.vue'

const connectionStore = useConnectionStore()
const queryStore = useQueryStore()

const selectedConnectionId = ref(null)
const readOnlyMode = ref(false)
const showHistory = ref(false)

// EXPLAIN 相关状态
const showExplainPlan = ref(false)
const explainLoading = ref(false)
const explainAnalyze = ref(false)

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

// 获取当前连接的数据库类型
const currentDbType = computed(() => {
  const conn = connectionStore.connections.find(c => c.id === selectedConnectionId.value)
  return conn?.db_type || 'mysql'
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
  // 执行普通查询时关闭 EXPLAIN 面板
  showExplainPlan.value = false
  try {
    await queryStore.executeQuery(selectedConnectionId.value, sql)
  } catch (error) {
    // 错误已在 store 中处理
  }
}

// EXPLAIN 按钮处理
function handleExplain(analyze) {
  if (!selectedConnectionId.value) {
    ElMessage.warning('请先选择数据库连接')
    return
  }
  const sql = currentSql.value
  if (!sql || !sql.trim()) {
    ElMessage.warning('请输入 SQL 查询语句')
    return
  }
  explainAnalyze.value = analyze
  showExplainPlan.value = true
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
    // 错误已在 store 中处理
  }
}

async function handleExport(format) {
  if (!selectedConnectionId.value || !currentTab.value?.sql) return
  try {
    if (format === 'excel') {
      const response = await queryStore.exportResults(
        selectedConnectionId.value,
        currentTab.value.sql,
        format
      )
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
  background: var(--qc-bg, #fff);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.console-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--qc-border, #e4e7ed);
  background: var(--qc-toolbar-bg, #fafafa);
}
.toolbar-left { display: flex; align-items: center; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.tab-bar {
  display: flex; align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid var(--qc-border, #e4e7ed);
  background: var(--qc-bg, #fff);
}
.query-tabs { flex: 1; }
.query-tabs :deep(.el-tabs__header) { margin: 0; }
.query-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.add-tab-btn { margin-left: 4px; flex-shrink: 0; }
.console-content { flex: 1; display: flex; overflow: hidden; position: relative; }
.editor-area {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; min-width: 0;
}
.editor-section {
  height: 40%; min-height: 150px;
  display: flex; flex-direction: column;
  position: relative;
}

/* EXPLAIN 按钮条 */
.explain-btn-bar {
  display: flex; gap: 6px;
  padding: 4px 8px;
  border-top: 1px solid var(--qc-border, #e4e7ed);
  background: var(--qc-toolbar-bg, #fafafa);
  flex-shrink: 0;
}

.horizontal-splitter {
  height: 3px; background: var(--qc-border, #e4e7ed); flex-shrink: 0;
}
.results-section { flex: 1; overflow: auto; }

/* EXPLAIN 面板 */
.explain-panel {
  display: flex; flex-direction: column; height: 100%;
}
.explain-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--qc-border, #e4e7ed);
  background: var(--qc-toolbar-bg, #fafafa);
  flex-shrink: 0;
}
.explain-panel-title {
  font-size: 13px; font-weight: 600;
  color: var(--qc-text, #303133);
}
.explain-panel-body { flex: 1; overflow: auto; }

.history-drawer {
  width: 320px;
  border-left: 1px solid var(--qc-border, #e4e7ed);
  background: var(--qc-bg, #fff);
  overflow: hidden; flex-shrink: 0;
}
.slide-right-enter-active, .slide-right-leave-active { transition: all 0.3s ease; }
.slide-right-enter-from, .slide-right-leave-to { width: 0; opacity: 0; }

/* 暗色模式 */
:global(html.dark) .query-console-page {
  --qc-bg: #141414; --qc-border: #363636;
  --qc-toolbar-bg: #1d1e1f; --qc-text: #e5eaf3;
}
</style>
