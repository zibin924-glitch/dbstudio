<template>
  <div class="table-detail" v-loading="loading">
    <div class="detail-header">
      <h3 class="detail-title">
        <el-icon><Grid /></el-icon>
        {{ schema }}.{{ tableName }}
      </h3>
      <el-button text size="small" @click="refreshAll">
        <el-icon><Refresh /></el-icon>
        Refresh
      </el-button>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="detail-tabs">
      <!-- Columns Tab -->
      <el-tab-pane label="Columns" name="columns">
        <el-table :data="columns" stripe border size="small" style="width: 100%;" max-height="500">
          <el-table-column type="index" width="50" label="#" />
          <el-table-column prop="name" label="Column Name" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{ 'pk-column': row.is_primary_key || row.pk }">
                <el-icon v-if="row.is_primary_key || row.pk" size="12" class="pk-icon"><Key /></el-icon>
                {{ row.name || row.column_name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="data_type" label="Data Type" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.data_type || row.type || row.column_type || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="nullable" label="Nullable" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="(row.nullable || row.is_nullable === 'YES') ? 'success' : 'danger'" size="small">
                {{ (row.nullable || row.is_nullable === 'YES') ? 'Yes' : 'No' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="default" label="Default" min-width="100" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.default || row.column_default || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="auto_increment" label="Auto Inc" width="85" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.auto_increment || row.extra?.includes('auto_increment')" color="#409eff"><Check /></el-icon>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="comment" label="Comment" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.comment || row.column_comment || '' }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Indexes Tab -->
      <el-tab-pane label="Indexes" name="indexes">
        <el-table :data="indexes" stripe border size="small" style="width: 100%;" max-height="500">
          <el-table-column prop="name" label="Index Name" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.name || row.index_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="Type" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.type || row.index_type || 'BTREE' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="columns" label="Columns" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              {{ Array.isArray(row.columns) ? row.columns.join(', ') : (row.columns || row.column_name || '-') }}
            </template>
          </el-table-column>
          <el-table-column prop="unique" label="Unique" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="(row.unique || row.non_unique === 0) ? 'warning' : 'info'" size="small">
                {{ (row.unique || row.non_unique === 0) ? 'Yes' : 'No' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="indexes.length === 0" description="No indexes found" :image-size="60" />
      </el-tab-pane>

      <!-- Foreign Keys Tab -->
      <el-tab-pane label="Foreign Keys" name="foreign_keys">
        <el-table :data="foreignKeys" stripe border size="small" style="width: 100%;" max-height="500">
          <el-table-column prop="name" label="Constraint Name" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.name || row.constraint_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="source_column" label="Source Column" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.source_column || row.column_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="target_table" label="Target Table" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.target_table || row.referenced_table_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="target_column" label="Target Column" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.target_column || row.referenced_column_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="on_update" label="On Update" width="100">
            <template #default="{ row }">
              {{ row.on_update || row.update_rule || 'NO ACTION' }}
            </template>
          </el-table-column>
          <el-table-column prop="on_delete" label="On Delete" width="100">
            <template #default="{ row }">
              {{ row.on_delete || row.delete_rule || 'NO ACTION' }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="foreignKeys.length === 0" description="No foreign keys found" :image-size="60" />
      </el-tab-pane>

      <!-- Properties Tab -->
      <el-tab-pane label="Properties" name="properties">
        <el-descriptions :column="2" border size="small" class="props-desc">
          <el-descriptions-item label="Table Name">{{ tableName }}</el-descriptions-item>
          <el-descriptions-item label="Schema">{{ schema }}</el-descriptions-item>
          <el-descriptions-item label="Engine">{{ stats.engine || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Charset">{{ stats.charset || stats.character_set || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Collation">{{ stats.collation || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Row Count">{{ stats.row_count ?? stats.rows ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="Data Size">{{ formatBytes(stats.data_size || stats.data_length) }}</el-descriptions-item>
          <el-descriptions-item label="Index Size">{{ formatBytes(stats.index_size || stats.index_length) }}</el-descriptions-item>
          <el-descriptions-item label="Auto Increment">{{ stats.auto_increment || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Created">{{ stats.create_time || stats.created || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Updated">{{ stats.update_time || stats.updated || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Comment" :span="2">{{ stats.comment || stats.table_comment || '' }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- Data Preview Tab -->
      <el-tab-pane label="Data Preview" name="data_preview">
        <div class="preview-toolbar">
          <el-button size="small" @click="loadPreviewData" :loading="previewLoading">
            <el-icon><Refresh /></el-icon>
            Refresh
          </el-button>
          <span class="preview-info" v-if="previewTotal > 0">
            Showing {{ (previewPage - 1) * previewPageSize + 1 }}-{{ Math.min(previewPage * previewPageSize, previewTotal) }} of {{ previewTotal }}
          </span>
        </div>
        <el-table
          :data="previewRows"
          stripe
          border
          size="small"
          style="width: 100%;"
          max-height="400"
          v-loading="previewLoading"
        >
          <el-table-column
            v-for="col in previewColumns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
            show-overflow-tooltip
          />
        </el-table>
        <div class="preview-pagination" v-if="previewTotal > previewPageSize">
          <el-pagination
            v-model:current-page="previewPage"
            :page-size="previewPageSize"
            :total="previewTotal"
            layout="prev, pager, next"
            small
            @current-change="loadPreviewData"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getColumns, getIndexes, getForeignKeys, getTableData, getStats } from '@/api/index.js'

const props = defineProps({
  connectionId: { type: [String, Number], required: true },
  tableName: { type: String, required: true },
  schema: { type: String, required: true }
})

const loading = ref(false)
const activeTab = ref('columns')

// Columns
const columns = ref([])
// Indexes
const indexes = ref([])
// Foreign Keys
const foreignKeys = ref([])
// Properties / Stats
const stats = ref({})

// Data Preview
const previewColumns = ref([])
const previewRows = ref([])
const previewTotal = ref(0)
const previewPage = ref(1)
const previewPageSize = 100
const previewLoading = ref(false)

watch(
  () => [props.connectionId, props.tableName, props.schema],
  () => {
    if (props.connectionId && props.tableName && props.schema) {
      refreshAll()
    }
  },
  { immediate: true }
)

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([
      loadColumns(),
      loadIndexes(),
      loadForeignKeys(),
      loadStats(),
      loadPreviewData()
    ])
  } catch (error) {
    console.error('Failed to load table details:', error)
  } finally {
    loading.value = false
  }
}

async function loadColumns() {
  try {
    const response = await getColumns(props.connectionId, props.schema, props.tableName)
    columns.value = response.data || response || []
  } catch (error) {
    columns.value = []
  }
}

async function loadIndexes() {
  try {
    const response = await getIndexes(props.connectionId, props.schema, props.tableName)
    indexes.value = response.data || response || []
  } catch (error) {
    indexes.value = []
  }
}

async function loadForeignKeys() {
  try {
    const response = await getForeignKeys(props.connectionId, props.schema, props.tableName)
    foreignKeys.value = response.data || response || []
  } catch (error) {
    foreignKeys.value = []
  }
}

async function loadStats() {
  try {
    const response = await getStats(props.connectionId)
    const allStats = response.data || response || {}
    // Try to find stats for this specific table
    if (Array.isArray(allStats)) {
      const tableStats = allStats.find(
        s => (s.table_name === props.tableName || s.name === props.tableName) &&
             (s.table_schema === props.schema || s.schema === props.schema || !s.table_schema)
      )
      stats.value = tableStats || {}
    } else if (allStats.tables) {
      const tableStats = allStats.tables.find(
        s => (s.table_name === props.tableName || s.name === props.tableName)
      )
      stats.value = tableStats || allStats
    } else {
      stats.value = allStats
    }
  } catch (error) {
    stats.value = {}
  }
}

async function loadPreviewData() {
  previewLoading.value = true
  try {
    const response = await getTableData(
      props.connectionId,
      props.schema,
      props.tableName,
      previewPage.value,
      previewPageSize
    )
    const data = response.data || response
    previewColumns.value = data.columns || []
    previewRows.value = data.rows || []
    previewTotal.value = data.total || (data.rows ? data.rows.length : 0)
  } catch (error) {
    previewColumns.value = []
    previewRows.value = []
    previewTotal.value = 0
  } finally {
    previewLoading.value = false
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

defineExpose({ refreshAll })
</script>

<style scoped>
.table-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.detail-tabs {
  flex: 1;
  overflow: auto;
  border: none;
}

.detail-tabs :deep(.el-tabs__content) {
  padding: 12px;
}

.pk-column {
  font-weight: 600;
  color: #e6a23c;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pk-icon {
  color: #e6a23c;
}

.text-muted {
  color: #c0c4cc;
}

.props-desc {
  max-width: 800px;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.preview-info {
  font-size: 13px;
  color: #909399;
}

.preview-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}
</style>
