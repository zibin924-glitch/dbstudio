<template>
  <div class="query-history-container">
    <div class="history-header">
      <h4 class="history-title">Query History</h4>
      <el-button text size="small" @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <div class="history-search">
      <el-input
        v-model="searchQuery"
        placeholder="Search queries..."
        clearable
        size="small"
        prefix-icon="Search"
        @input="handleSearch"
        @clear="handleSearch"
      />
    </div>

    <div class="history-list" v-loading="loading">
      <div
        v-for="item in history"
        :key="item.id"
        class="history-item"
        @click="handleSelect(item)"
      >
        <div class="item-header">
          <span class="item-time">{{ formatTime(item.executed_at || item.created_at || item.timestamp) }}</span>
          <div class="item-actions">
            <el-tag v-if="item.duration_ms" size="small" type="info" class="duration-tag">
              {{ item.duration_ms }}ms
            </el-tag>
            <el-icon
              :class="['favorite-icon', { 'is-favorite': item.is_favorite }]"
              @click.stop="handleToggleFavorite(item)"
            >
              <StarFilled v-if="item.is_favorite" />
              <Star v-else />
            </el-icon>
          </div>
        </div>
        <div class="item-sql" :title="item.sql">
          <code>{{ truncateSql(item.sql) }}</code>
        </div>
        <div class="item-meta">
          <span v-if="item.row_count != null" class="meta-row-count">
            {{ item.row_count }} rows
          </span>
          <span v-if="item.status" class="meta-status" :class="item.status">
            {{ item.status }}
          </span>
        </div>
      </div>

      <el-empty
        v-if="!loading && history.length === 0"
        :description="searchQuery ? 'No matching queries' : 'No query history yet'"
        :image-size="60"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQueryStore } from '@/stores/query.js'

const props = defineProps({
  connectionId: { type: [String, Number], default: null }
})

const emit = defineEmits(['select'])

const queryStore = useQueryStore()
const searchQuery = ref('')
const loading = ref(false)

const history = ref([])

onMounted(() => {
  handleRefresh()
})

async function handleRefresh() {
  loading.value = true
  try {
    await queryStore.fetchHistory(props.connectionId, searchQuery.value)
    history.value = queryStore.history
  } catch (error) {
    history.value = []
  } finally {
    loading.value = false
  }
}

let searchTimeout = null
function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    loading.value = true
    try {
      await queryStore.fetchHistory(props.connectionId, searchQuery.value)
      history.value = queryStore.history
    } catch (error) {
      history.value = []
    } finally {
      loading.value = false
    }
  }, 300)
}

function handleSelect(item) {
  emit('select', item.sql)
}

async function handleToggleFavorite(item) {
  try {
    await queryStore.toggleFavorite(item.id)
    item.is_favorite = !item.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}

function truncateSql(sql) {
  if (!sql) return ''
  const singleLine = sql.replace(/\s+/g, ' ').trim()
  return singleLine.length > 120 ? singleLine.substring(0, 120) + '...' : singleLine
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return timestamp
  }
}

defineExpose({ refresh: handleRefresh })
</script>

<style scoped>
.query-history-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.history-search {
  padding: 0 12px 8px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.history-item {
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f5f7fa;
  border-color: #c6e2ff;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.item-time {
  font-size: 11px;
  color: #909399;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.duration-tag {
  transform: scale(0.85);
}

.favorite-icon {
  cursor: pointer;
  font-size: 16px;
  color: #c0c4cc;
  transition: color 0.2s;
}

.favorite-icon:hover {
  color: #e6a23c;
}

.favorite-icon.is-favorite {
  color: #e6a23c;
}

.item-sql {
  margin-bottom: 4px;
}

.item-sql code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #303133;
  line-height: 1.5;
  word-break: break-all;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #909399;
}

.meta-row-count {
  color: #67c23a;
}

.meta-status.success {
  color: #67c23a;
}

.meta-status.error {
  color: #f56c6c;
}
</style>
