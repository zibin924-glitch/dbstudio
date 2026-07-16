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
        <el-tag size="small" v-if="selectedRows.length > 0" type="warning">
          {{ selectedRows.length }} selected
        </el-tag>
      </div>
      <div class="result-actions" v-if="hasData">
        <el-dropdown
          @command="handleExportSelected"
          trigger="click"
          :disabled="selectedRows.length === 0"
        >
          <el-button
            size="small"
            plain
            type="warning"
            :disabled="selectedRows.length === 0"
          >
            Export Selected ({{ selectedRows.length }})
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="csv">
                <el-icon><Document /></el-icon> Selected as CSV
              </el-dropdown-item>
              <el-dropdown-item command="json">
                <el-icon><Document /></el-icon> Selected as JSON
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
        ref="tableRef"
        :data="filteredRows"
        stripe
        border
        size="small"
        style="width: 100%;"
        max-height="400"
        highlight-current-row
        :default-sort="{ order: null }"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column type="index" width="60" label="#" />
        <el-table-column
          v-for="col in columns"
          :key="col"
          :prop="col"
          :label="col"
          min-width="130"
          sortable
          :filter-method="(value, row) => filterMethod(value, row, col)"
          :filters="[]"
        >
          <template #header>
            <div class="column-header">
              <span class="column-header-label" :title="col">{{ col }}</span>
              <el-popover
                :visible="activeFilterCol === col"
                placement="bottom"
                :width="200"
                trigger="click"
                @update:visible="(val) => { if (!val) activeFilterCol = null }"
              >
                <template #reference>
                  <el-icon
                    class="filter-icon"
                    :class="{ 'filter-active': columnFilters[col] }"
                    @click.stop="toggleFilterPopover(col)"
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover-content">
                  <el-input
                    v-model="filterInputs[col]"
                    placeholder="Filter value..."
                    size="small"
                    clearable
                    @input="applyColumnFilter(col)"
                    @clear="clearColumnFilter(col)"
                    @click.stop
                  />
                  <div class="filter-popover-actions">
                    <el-button size="small" text type="primary" @click="clearColumnFilter(col)">Reset</el-button>
                  </div>
                </div>
              </el-popover>
            </div>
          </template>
          <template #default="{ row }">
            <!-- NULL rendering -->
            <span v-if="row[col] === null || row[col] === undefined" class="cell-null">NULL</span>
            <!-- Boolean rendering -->
            <el-tag v-else-if="isBooleanValue(row[col])" :type="toBool(row[col]) ? 'success' : 'danger'" size="small">
              {{ toBool(row[col]) ? 'true' : 'false' }}
            </el-tag>
            <!-- JSON rendering -->
            <el-popover
              v-else-if="isJsonString(row[col])"
              placement="bottom"
              :width="400"
              trigger="click"
            >
              <template #reference>
                <span class="cell-json-preview" @click.stop>
                  {&hellip;} <span class="cell-json-hint">{{ truncateValue(String(row[col]), 50) }}</span>
                </span>
              </template>
              <pre class="cell-json-formatted">{{ formatJson(row[col]) }}</pre>
            </el-popover>
            <!-- Date/datetime rendering -->
            <span v-else-if="isDateValue(row[col])" class="cell-date">
              {{ formatDate(row[col]) }}
            </span>
            <!-- Long text with show more -->
            <span v-else-if="isLongText(row[col])" class="cell-long-text">
              <span v-if="!expandedCells[`${col}-${rowIndex(row)}`]">
                {{ truncateValue(String(row[col]), 100) }}
                <el-button link type="primary" size="small" @click.stop="expandCell(col, rowIndex(row))">...show more</el-button>
              </span>
              <span v-else>
                {{ row[col] }}
                <el-button link type="primary" size="small" @click.stop="collapseCell(col, rowIndex(row))">show less</el-button>
              </span>
            </span>
            <!-- Default rendering -->
            <span v-else class="cell-default">{{ row[col] }}</span>
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
import { ref, computed, reactive, watch } from 'vue'
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
const tableRef = ref(null)
const selectedRows = ref([])
const expandedCells = reactive({})

// Column filter state
const activeFilterCol = ref(null)
const filterInputs = reactive({})
const columnFilters = reactive({})

const hasData = computed(() => props.columns.length > 0 && props.rows.length > 0)
const hasError = computed(() => !!props.error)

// Filtered rows based on column filters
const filteredRows = computed(() => {
  const activeFilters = Object.entries(columnFilters).filter(([, v]) => v)
  if (activeFilters.length === 0) return props.rows
  return props.rows.filter(row => {
    return activeFilters.every(([col, filterVal]) => {
      const cellVal = row[col]
      if (cellVal === null || cellVal === undefined) {
        return filterVal.toLowerCase() === 'null'
      }
      return String(cellVal).toLowerCase().includes(filterVal.toLowerCase())
    })
  })
})

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

// ---- Data-type detection helpers ----

function isBooleanValue(val) {
  if (typeof val === 'boolean') return true
  if (typeof val === 'number') return false
  if (typeof val === 'string') {
    const lower = val.toLowerCase()
    return lower === 'true' || lower === 'false' || lower === '0' || lower === '1'
  }
  return false
}

function toBool(val) {
  if (typeof val === 'boolean') return val
  if (typeof val === 'string') {
    return val.toLowerCase() === 'true' || val === '1'
  }
  return Boolean(val)
}

function isJsonString(val) {
  if (typeof val !== 'string') return false
  const trimmed = val.trim()
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed)
      return true
    } catch {
      return false
    }
  }
  return false
}

function formatJson(val) {
  try {
    return JSON.stringify(JSON.parse(val), null, 2)
  } catch {
    return String(val)
  }
}

// ISO 8601 and common date/datetime patterns
const DATE_REGEX = /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$/

function isDateValue(val) {
  if (typeof val !== 'string') return false
  return DATE_REGEX.test(val.trim())
}

function formatDate(val) {
  if (!val) return val
  const trimmed = val.trim()
  // If it already looks like a well-formatted datetime, return as-is with T replaced by space
  return trimmed.replace('T', ' ').replace('Z', '')
}

function isLongText(val) {
  return typeof val === 'string' && val.length > 100
}

function truncateValue(str, maxLen) {
  if (str.length <= maxLen) return str
  return str.substring(0, maxLen) + '...'
}

function rowIndex(row) {
  return props.rows.indexOf(row)
}

function expandCell(col, idx) {
  expandedCells[`${col}-${idx}`] = true
}

function collapseCell(col, idx) {
  delete expandedCells[`${col}-${idx}`]
}

// ---- Column filter logic ----

function toggleFilterPopover(col) {
  activeFilterCol.value = activeFilterCol.value === col ? null : col
}

function applyColumnFilter(col) {
  const val = filterInputs[col]
  if (val !== undefined && val !== null && val !== '') {
    columnFilters[col] = val
  } else {
    delete columnFilters[col]
  }
}

function clearColumnFilter(col) {
  delete columnFilters[col]
  filterInputs[col] = ''
  activeFilterCol.value = null
}

// Placeholder for el-table's filter-method (we use computed filteredRows instead)
function filterMethod() {
  return true
}

// ---- Export functions ----

function handleExport(format) {
  emit('export', format)
  if (format === 'csv') {
    downloadCsv(props.rows)
  } else if (format === 'json') {
    downloadJson(props.rows)
  }
}

function handleExportSelected(format) {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('No rows selected. Please select rows first.')
    return
  }

  if (format === 'json') {
    downloadJson(selectedRows.value, 'selected_rows.json')
  } else {
    downloadCsv(selectedRows.value, 'selected_rows.csv')
  }
  ElMessage.success(`Exported ${selectedRows.value.length} selected rows as ${format?.toUpperCase() || 'CSV'}`)
}

function downloadCsv(rowsToExport, filename = 'query_result.csv') {
  if (!rowsToExport || rowsToExport.length === 0) return

  const header = props.columns.join(',')
  const csvRows = rowsToExport.map(row => {
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
  downloadFile(csv, filename, 'text/csv')
  ElMessage.success('CSV exported')
}

function downloadJson(rowsToExport, filename = 'query_result.json') {
  if (!rowsToExport || rowsToExport.length === 0) return

  const json = JSON.stringify(rowsToExport, null, 2)
  downloadFile(json, filename, 'application/json')
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

// Clear filter state when data changes
watch(() => props.rows, () => {
  Object.keys(columnFilters).forEach(k => delete columnFilters[k])
  Object.keys(filterInputs).forEach(k => delete filterInputs[k])
  selectedRows.value = []
})
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

/* ---- Column header with filter ---- */
.column-header {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.column-header-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-icon {
  font-size: 14px;
  color: #c0c4cc;
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.2s;
}

.filter-icon:hover {
  color: #409eff;
}

.filter-icon.filter-active {
  color: #409eff;
}

.filter-popover-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-popover-actions {
  display: flex;
  justify-content: flex-end;
}

/* ---- Cell type styles ---- */
.cell-null {
  color: #c0c4cc;
  font-style: italic;
}

.cell-json-preview {
  cursor: pointer;
  color: #e6a23c;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}

.cell-json-preview .cell-json-hint {
  color: #909399;
  font-family: inherit;
}

.cell-json-formatted {
  max-height: 300px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.cell-date {
  color: #409eff;
  font-variant-numeric: tabular-nums;
}

.cell-long-text {
  word-break: break-word;
}

.cell-default {
  /* default cell rendering - no special styling */
}

/* Legacy class kept for backward compat */
.null-value {
  color: #c0c4cc;
  font-style: italic;
}
</style>
