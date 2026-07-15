<template>
  <div class="query-result-container">
    <div class="result-toolbar">
      <div class="result-stats">
        <el-tag size="small" v-if="rows.length > 0" type="success">
          {{ total }} rows
        </el-tag>
        <el-tag size="small" v-if="durationMs != null" type="info">
          {{ durationMs }}ms
        </el-tag>
        <el-tag size="small" v-if="!hasData && !hasError" type="info">
          No results
        </el-tag>
      </div>
      <div class="result-actions" v-if="hasData">
        <el-dropdown @command="handleExport" trigger="click">
          <el-button size="small" plain>
            Export <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="csv">
                <el-icon><Document /></el-icon> Export CSV
              </el-dropdown-item>
              <el-dropdown-item command="json">
                <el-icon><Document /></el-icon> Export JSON
              </el-dropdown-item>
              <el-dropdown-item command="excel">
                <el-icon><Document /></el-icon> Export Excel
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- Error Display -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      class="result-error"
    />

    <!-- Results Table -->
    <div class="result-table-wrapper" v-if="hasData">
      <el-table
        :data="paginatedRows"
        stripe
        border
        size="small"
        style="width: 100%;"
        max-height="400"
        highlight-current-row
        :default-sort="{ order: null }"
      >
        <el-table-column type="index" width="60" label="#" />
        <el-table-column
          v-for="col in columns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="130"
          show-overflow-tooltip
          sortable
        >
          <template #default="{ row }">
            <span :class="{ 'null-value': row[col] === null }">
              {{ row[col] === null ? 'NULL' : row[col] }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination -->
    <div class="result-pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSizeLocal"
        :page-sizes="[25, 50, 100, 200]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        small
        @current-change="$emit('page-change', currentPage)"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 50 },
  durationMs: { type: Number, default: null },
  error: { type: String, default: null }
})

const emit = defineEmits(['page-change', 'export', 'size-change'])

const currentPage = ref(props.page)
const pageSizeLocal = ref(props.pageSize)

const hasData = computed(() => props.columns.length > 0 && props.rows.length > 0)
const hasError = computed(() => !!props.error)

const paginatedRows = computed(() => props.rows)

function handleExport(format) {
  emit('export', format)

  // Client-side export fallback
  if (format === 'csv') {
    downloadCsv()
  } else if (format === 'json') {
    downloadJson()
  }
}

function downloadCsv() {
  if (!hasData.value) return

  const header = props.columns.join(',')
  const csvRows = props.rows.map(row => {
    return props.columns.map(col => {
      const val = row[col]
      if (val === null || val === undefined) return ''
      const str = String(val)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    }).join(',')
  })

  const csv = [header, ...csvRows].join('\n')
  downloadFile(csv, 'query_result.csv', 'text/csv')
  ElMessage.success('CSV exported')
}

function downloadJson() {
  if (!hasData.value) return

  const json = JSON.stringify(props.rows, null, 2)
  downloadFile(json, 'query_result.json', 'application/json')
  ElMessage.success('JSON exported')
}

function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function handleSizeChange(size) {
  emit('size-change', size)
}
</script>

<style scoped>
.query-result-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.result-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-error {
  margin: 8px;
}

.result-table-wrapper {
  flex: 1;
  overflow: auto;
}

.result-pagination {
  padding: 8px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #e4e7ed;
}

.null-value {
  color: #c0c4cc;
  font-style: italic;
}
</style>
