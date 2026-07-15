<template>
  <div class="connections-page">
    <div class="page-header">
      <h2 class="page-title">Database Connections</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        Add Connection
      </el-button>
    </div>

    <!-- Group Filter Tabs -->
    <el-tabs v-model="activeGroup" class="group-tabs" v-if="groups.length > 1">
      <el-tab-pane label="All" name="all" />
      <el-tab-pane
        v-for="group in groups"
        :key="group"
        :label="group"
        :name="group"
      />
    </el-tabs>

    <!-- Connection Cards -->
    <div class="connection-grid" v-loading="connectionStore.loading">
      <div
        v-for="conn in filteredConnections"
        :key="conn.id"
        class="connection-card"
        :class="{ 'is-active': connectionStore.currentConnection?.id === conn.id }"
        @click="selectConnection(conn)"
      >
        <div class="card-header">
          <div class="card-type-badge" :class="conn.db_type">
            {{ (conn.db_type || 'unknown').toUpperCase() }}
          </div>
          <div class="card-actions">
            <el-button text size="small" @click.stop="openEditDialog(conn)" title="Edit">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button text size="small" @click.stop="handleTest(conn)" title="Test">
              <el-icon><Connection /></el-icon>
            </el-button>
            <el-popconfirm
              title="Delete this connection?"
              confirm-button-text="Delete"
              cancel-button-text="Cancel"
              @confirm="handleDelete(conn)"
            >
              <template #reference>
                <el-button text size="small" type="danger" @click.stop title="Delete">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
        <h3 class="card-name">{{ conn.name }}</h3>
        <div class="card-info">
          <span class="info-item">
            <el-icon><Monitor /></el-icon>
            {{ conn.host }}:{{ conn.port }}
          </span>
          <span class="info-item">
            <el-icon><Coin /></el-icon>
            {{ conn.database_name || '-' }}
          </span>
          <span class="info-item">
            <el-icon><User /></el-icon>
            {{ conn.username }}
          </span>
        </div>
        <div class="card-footer" v-if="conn.tags && conn.tags.length > 0">
          <el-tag
            v-for="tag in conn.tags"
            :key="tag"
            size="small"
            type="info"
            class="card-tag"
          >
            {{ tag }}
          </el-tag>
        </div>
        <div class="card-group" v-if="conn.group_name">
          <el-tag size="small" effect="plain">{{ conn.group_name }}</el-tag>
        </div>
      </div>

      <el-empty
        v-if="!connectionStore.loading && filteredConnections.length === 0"
        description="No connections yet. Click 'Add Connection' to get started."
        :image-size="120"
      >
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          Add Connection
        </el-button>
      </el-empty>
    </div>

    <!-- Connection Form Dialog -->
    <ConnectionForm
      v-model:visible="formVisible"
      :connection="editingConnection"
      @saved="onFormSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import ConnectionForm from '@/components/ConnectionForm.vue'

const connectionStore = useConnectionStore()

const formVisible = ref(false)
const editingConnection = ref(null)
const activeGroup = ref('all')

const groups = computed(() => connectionStore.groups)

const filteredConnections = computed(() => {
  if (activeGroup.value === 'all') {
    return connectionStore.connections
  }
  return connectionStore.connections.filter(
    c => (c.group_name || 'Default') === activeGroup.value
  )
})

onMounted(() => {
  connectionStore.fetchConnections()
})

function openCreateDialog() {
  editingConnection.value = null
  formVisible.value = true
}

function openEditDialog(conn) {
  editingConnection.value = { ...conn }
  formVisible.value = true
}

function selectConnection(conn) {
  connectionStore.setCurrentConnection(conn)
  ElMessage.success(`Switched to: ${conn.name}`)
}

async function handleTest(conn) {
  try {
    const result = await connectionStore.testConnection(conn)
    const data = result.data || result
    if (data.success || data.status === 'ok') {
      ElMessage.success(`Connection "${conn.name}" is working!`)
    } else {
      ElMessage.error(data.message || `Connection "${conn.name}" failed`)
    }
  } catch (error) {
    ElMessage.error(`Failed to test connection "${conn.name}"`)
  }
}

async function handleDelete(conn) {
  try {
    await connectionStore.deleteConnection(conn.id)
    ElMessage.success(`Connection "${conn.name}" deleted`)
  } catch (error) {
    ElMessage.error('Failed to delete connection')
  }
}

function onFormSaved() {
  connectionStore.fetchConnections()
}
</script>

<style scoped>
.connections-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.group-tabs {
  margin-bottom: 16px;
}

.group-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.connection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  align-content: start;
}

.connection-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.25s;
  position: relative;
}

.connection-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #c6e2ff;
}

.connection-card.is-active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card-type-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.card-type-badge.mysql {
  background: #e8f4fd;
  color: #00758f;
}

.card-type-badge.postgresql {
  background: #e8f0fe;
  color: #336791;
}

.card-type-badge.oracle {
  background: #fdf2e8;
  color: #f80000;
}

.card-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.connection-card:hover .card-actions {
  opacity: 1;
}

.card-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 10px;
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.info-item .el-icon {
  color: #909399;
  font-size: 13px;
}

.card-footer {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.card-tag {
  transform: scale(0.9);
  transform-origin: left;
}

.card-group {
  margin-top: 8px;
}
</style>
