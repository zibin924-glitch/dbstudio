<template>
  <div class="explorer-page">
    <!-- 左侧面板: 连接选择 + 树 -->
    <div class="explorer-left">
      <div class="panel-header">
        <h3 class="panel-title">Structure Browser</h3>
      </div>
      <div class="connection-selector">
        <el-select
          v-model="selectedConnectionId"
          placeholder="Select connection"
          filterable
          style="width: 100%;"
          @change="onConnectionChange"
        >
          <el-option
            v-for="conn in connectionStore.connections"
            :key="conn.id"
            :label="`${conn.name} (${conn.db_type})`"
            :value="conn.id"
          />
        </el-select>
      </div>
      <div class="tree-panel">
        <DbTree
          ref="dbTreeRef"
          :connection-id="selectedConnectionId"
          @node-select="onNodeSelect"
        />
      </div>
    </div>

    <!-- 拖拽分隔条 -->
    <div class="resize-handle" @mousedown="startResize"></div>

    <!-- 右侧面板: 表详情 / 统计 / ER 图 -->
    <div class="explorer-right" :style="{ width: rightPanelWidth + 'px' }">
      <!-- ER 图全屏覆盖 -->
      <template v-if="showErDiagram">
        <div class="er-overlay">
          <div class="er-overlay-header">
            <span class="er-overlay-title">
              <el-icon><Share /></el-icon>
              ER 关系图 — {{ currentConnectionName }}
            </span>
            <el-button size="small" @click="showErDiagram = false">
              <el-icon><Close /></el-icon>
              关闭
            </el-button>
          </div>
          <div class="er-overlay-body">
            <ErDiagram :connection-id="selectedConnectionId" />
          </div>
        </div>
      </template>

      <template v-else-if="selectedNode && (selectedNode.type === 'table' || selectedNode.type === 'view')">
        <TableDetail
          :key="`${selectedConnectionId}-${selectedNode.schema}-${selectedNode.tableName}`"
          :connection-id="selectedConnectionId"
          :table-name="selectedNode.tableName"
          :schema="selectedNode.schema"
        />
      </template>

      <template v-else-if="selectedConnectionId && stats">
        <div class="stats-panel">
          <h3 class="stats-title">
            <el-icon><DataAnalysis /></el-icon>
            Database Overview
          </h3>
          <el-descriptions :column="2" border size="small" class="stats-desc">
            <el-descriptions-item label="Connection">
              {{ currentConnectionName }}
            </el-descriptions-item>
            <el-descriptions-item label="Database Type">
              {{ currentConnectionType }}
            </el-descriptions-item>
            <el-descriptions-item label="Total Tables">
              {{ stats.total_tables ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Total Views">
              {{ stats.total_views ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Total Schemas">
              {{ stats.total_schemas ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Database Size">
              {{ formatBytes(stats.total_size || stats.database_size) }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- ER 图入口按钮 -->
          <div class="er-entry">
            <el-button type="primary" plain @click="showErDiagram = true">
              <el-icon><Share /></el-icon>
              查看 ER 关系图
            </el-button>
            <span class="er-entry-hint">可视化展示所有表和外键关系</span>
          </div>

          <div class="stats-tables-section" v-if="stats.tables && stats.tables.length > 0">
            <h4 class="stats-subtitle">Tables</h4>
            <el-table :data="stats.tables" stripe border size="small" max-height="400">
              <el-table-column prop="table_name" label="Table" min-width="160">
                <template #default="{ row }">
                  {{ row.table_name || row.name }}
                </template>
              </el-table-column>
              <el-table-column label="Rows" width="100" align="right">
                <template #default="{ row }">
                  {{ row.row_count ?? row.rows ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column label="Size" width="100" align="right">
                <template #default="{ row }">
                  {{ formatBytes(row.data_size || row.data_length) }}
                </template>
              </el-table-column>
              <el-table-column prop="engine" label="Engine" width="100">
                <template #default="{ row }">
                  {{ row.engine || '-' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="empty-panel">
          <el-empty description="Select a connection and browse tables">
            <template #image>
              <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
            </template>
          </el-empty>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useConnectionStore } from '@/stores/connection.js'
import { getStats } from '@/api/index.js'
import DbTree from '@/components/DbTree.vue'
import TableDetail from '@/components/TableDetail.vue'
import ErDiagram from '@/components/ErDiagram.vue'

const connectionStore = useConnectionStore()

const selectedConnectionId = ref(null)
const selectedNode = ref(null)
const dbTreeRef = ref(null)
const stats = ref(null)
const rightPanelWidth = ref(600)
const showErDiagram = ref(false)

const currentConnectionName = computed(() => {
  const conn = connectionStore.connections.find(c => c.id === selectedConnectionId.value)
  return conn?.name || ''
})

const currentConnectionType = computed(() => {
  const conn = connectionStore.connections.find(c => c.id === selectedConnectionId.value)
  return conn?.db_type || ''
})

onMounted(() => {
  connectionStore.fetchConnections().then(() => {
    if (connectionStore.currentConnection) {
      selectedConnectionId.value = connectionStore.currentConnection.id
      onConnectionChange(selectedConnectionId.value)
    }
  })
})

async function onConnectionChange(connId) {
  selectedNode.value = null
  stats.value = null
  showErDiagram.value = false
  if (connId) {
    try {
      const response = await getStats(connId)
      stats.value = response.data || response
    } catch (error) {
      stats.value = null
    }
  }
}

function onNodeSelect(node) {
  selectedNode.value = node
  // 选择表时自动关闭 ER 图，显示表详情
  if (node.type === 'table' || node.type === 'view') {
    showErDiagram.value = false
  }
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

// 面板宽度拖拽调整
let isResizing = false
let startX = 0
let startWidth = 0

function startResize(e) {
  isResizing = true
  startX = e.clientX
  startWidth = rightPanelWidth.value

  const onMouseMove = (e) => {
    if (!isResizing) return
    const diff = e.clientX - startX
    rightPanelWidth.value = Math.max(300, Math.min(1200, startWidth - diff))
  }

  const onMouseUp = () => {
    isResizing = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.explorer-page {
  display: flex;
  height: calc(100vh - 98px);
  background: var(--explorer-bg, #fff);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.explorer-left {
  width: 300px; min-width: 240px;
  display: flex; flex-direction: column;
  border-right: 1px solid var(--explorer-border, #e4e7ed);
}
.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--explorer-border, #e4e7ed);
}
.panel-title {
  font-size: 15px; font-weight: 600;
  color: var(--explorer-text, #303133); margin: 0;
}
.connection-selector {
  padding: 10px 12px;
  border-bottom: 1px solid var(--explorer-border-light, #ebeef5);
}
.tree-panel { flex: 1; overflow: auto; }
.resize-handle {
  width: 4px; background: var(--explorer-border, #e4e7ed);
  cursor: col-resize; transition: background 0.2s; flex-shrink: 0;
}
.resize-handle:hover { background: #409eff; }
.explorer-right { flex: 1; overflow: auto; min-width: 300px; position: relative; }

/* ER 图覆盖层 */
.er-overlay {
  display: flex; flex-direction: column; height: 100%;
}
.er-overlay-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--explorer-border, #e4e7ed);
  background: var(--explorer-bg, #fff);
  flex-shrink: 0;
}
.er-overlay-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 15px; font-weight: 600;
  color: var(--explorer-text, #303133);
}
.er-overlay-body { flex: 1; overflow: hidden; }

/* ER 图入口 */
.er-entry {
  display: flex; align-items: center; gap: 12px;
  margin: 16px 0;
}
.er-entry-hint {
  font-size: 12px; color: var(--explorer-muted, #909399);
}

.stats-panel { padding: 20px; }
.stats-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; font-weight: 600;
  color: var(--explorer-text, #303133); margin: 0 0 16px;
}
.stats-desc { margin-bottom: 24px; max-width: 700px; }
.stats-subtitle {
  font-size: 14px; font-weight: 600;
  color: var(--explorer-text-secondary, #606266); margin: 0 0 10px;
}
.stats-tables-section { margin-top: 8px; }
.empty-panel {
  display: flex; align-items: center; justify-content: center; height: 100%;
}

/* 暗色模式 */
:global(html.dark) .explorer-page {
  --explorer-bg: #141414; --explorer-border: #363636;
  --explorer-border-light: #414243;
  --explorer-text: #e5eaf3; --explorer-text-secondary: #cfd3dc;
  --explorer-muted: #8b8b8b;
}
</style>
