<template>
  <div class="er-diagram-wrapper" v-loading="loading" element-loading-text="正在加载 ER 图数据...">
    <!-- 工具栏 -->
    <div class="er-toolbar">
      <div class="er-toolbar-left">
        <el-button size="small" @click="resetView">
          <el-icon><RefreshRight /></el-icon>
          重置视图
        </el-button>
        <el-button size="small" @click="doAutoLayout">
          <el-icon><Grid /></el-icon>
          自动布局
        </el-button>
        <el-divider direction="vertical" />
        <el-tag size="small" type="info">表: {{ tables.length }}</el-tag>
        <el-tag size="small" type="warning">关系: {{ relationships.length }}</el-tag>
      </div>
      <div class="er-toolbar-right">
        <el-tag size="small" v-if="selectedTable" type="success">
          已选: {{ selectedTable.name }}
        </el-tag>
        <el-button size="small" @click="zoomIn" circle>
          <el-icon><Plus /></el-icon>
        </el-button>
        <el-button size="small" @click="zoomOut" circle>
          <el-icon><Minus /></el-icon>
        </el-button>
        <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
      </div>
    </div>

    <!-- SVG 画布 -->
    <div
      class="er-canvas-container"
      ref="canvasContainer"
      @mousedown="onCanvasMouseDown"
      @mousemove="onCanvasMouseMove"
      @mouseup="onCanvasMouseUp"
      @mouseleave="onCanvasMouseUp"
      @wheel.prevent="onCanvasWheel"
    >
      <svg
        ref="svgRef"
        width="100%"
        height="100%"
        :viewBox="`${viewBoxX} ${viewBoxY} ${viewBoxW} ${viewBoxH}`"
        class="er-svg"
      >
        <defs>
          <!-- 普通箭头 -->
          <marker id="er-arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#909399" />
          </marker>
          <marker id="er-arrow-hl" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#409eff" />
          </marker>
          <!-- "1" 端标记 -->
          <marker id="er-one" markerWidth="6" markerHeight="12" refX="0" refY="6" orient="auto">
            <line x1="3" y1="0" x2="3" y2="12" stroke="#909399" stroke-width="1.5" />
          </marker>
          <marker id="er-one-hl" markerWidth="6" markerHeight="12" refX="0" refY="6" orient="auto">
            <line x1="3" y1="0" x2="3" y2="12" stroke="#409eff" stroke-width="1.5" />
          </marker>
          <!-- "N" 端鸦爪标记 -->
          <marker id="er-many" markerWidth="12" markerHeight="12" refX="12" refY="6" orient="auto">
            <line x1="12" y1="6" x2="0" y2="0" stroke="#909399" stroke-width="1.5" />
            <line x1="12" y1="6" x2="0" y2="12" stroke="#909399" stroke-width="1.5" />
            <line x1="12" y1="6" x2="0" y2="6" stroke="#909399" stroke-width="1.5" />
          </marker>
          <marker id="er-many-hl" markerWidth="12" markerHeight="12" refX="12" refY="6" orient="auto">
            <line x1="12" y1="6" x2="0" y2="0" stroke="#409eff" stroke-width="1.5" />
            <line x1="12" y1="6" x2="0" y2="12" stroke="#409eff" stroke-width="1.5" />
            <line x1="12" y1="6" x2="0" y2="6" stroke="#409eff" stroke-width="1.5" />
          </marker>
        </defs>

        <!-- 关系连线层 -->
        <g class="er-relationships">
          <g v-for="(rel, idx) in relationships" :key="'rel-' + idx">
            <line
              :x1="rel.x1" :y1="rel.y1"
              :x2="rel.x2" :y2="rel.y2"
              :stroke="rel.highlighted ? '#409eff' : '#c0c4cc'"
              :stroke-width="rel.highlighted ? 2.5 : 1.5"
              :marker-start="rel.highlighted ? 'url(#er-one-hl)' : 'url(#er-one)'"
              :marker-end="getLineEndMarker(rel)"
            />
            <!-- 关系标签背景框 -->
            <rect
              :x="(rel.x1 + rel.x2) / 2 - 20"
              :y="(rel.y1 + rel.y2) / 2 - 10"
              width="40" height="20" rx="4"
              :fill="rel.highlighted ? '#ecf5ff' : '#f5f7fa'"
              :stroke="rel.highlighted ? '#409eff' : '#dcdfe6'"
              stroke-width="1"
            />
            <text
              :x="(rel.x1 + rel.x2) / 2"
              :y="(rel.y1 + rel.y2) / 2 + 4"
              text-anchor="middle"
              :fill="rel.highlighted ? '#409eff' : '#909399'"
              font-size="11" font-weight="500"
            >{{ rel.label }}</text>
          </g>
        </g>

        <!-- 表节点层 -->
        <g
          v-for="(table, idx) in tables"
          :key="'tbl-' + idx"
          class="er-table-group"
          :transform="`translate(${table.x}, ${table.y})`"
          @mousedown.stop="onTableMouseDown($event, table)"
          @click.stop="onTableClick(table)"
        >
          <!-- 阴影 -->
          <rect x="2" y="2" :width="TABLE_W" :height="calcTableH(table)" rx="6" fill="rgba(0,0,0,0.06)" />
          <!-- 表主体 -->
          <rect x="0" y="0" :width="TABLE_W" :height="calcTableH(table)" rx="6"
            :fill="isSelected(table) ? '#ecf5ff' : '#ffffff'"
            :stroke="isSelected(table) ? '#409eff' : schemaClr(table.schema, 'border')"
            stroke-width="1.5" class="er-table-body" />
          <!-- 表头背景 -->
          <rect x="0" y="0" :width="TABLE_W" height="32" rx="6" :fill="schemaClr(table.schema, 'header')" />
          <rect x="0" y="20" :width="TABLE_W" height="12" :fill="schemaClr(table.schema, 'header')" />
          <!-- 表名文字 -->
          <text :x="TABLE_W / 2" y="21" text-anchor="middle" fill="#fff" font-size="13" font-weight="600">{{ table.name }}</text>
          <line x1="0" y1="32" :x2="TABLE_W" y2="32" :stroke="schemaClr(table.schema, 'border')" stroke-width="0.5" opacity="0.3" />
          <!-- 列列表 -->
          <g v-for="(col, ci) in table.columns" :key="'c-' + ci">
            <rect x="1" :y="33 + ci * 22" :width="TABLE_W - 2" height="22" fill="transparent" class="er-col-row" />
            <text x="12" :y="48 + ci * 22" :fill="col.is_pk ? '#e6a23c' : '#606266'" font-size="12"
              :font-weight="col.is_pk ? '600' : '400'">
              <tspan v-if="col.is_pk" fill="#e6a23c">PK </tspan>{{ col.name }}
            </text>
            <text :x="TABLE_W - 12" :y="48 + ci * 22" text-anchor="end" fill="#909399" font-size="10">{{ col.type }}</text>
          </g>
        </g>
      </svg>
    </div>

    <!-- 图例面板 -->
    <div class="er-legend" v-if="schemaColors.length > 0">
      <div class="legend-title">Schema 图例</div>
      <div v-for="sc in schemaColors" :key="sc.schema" class="legend-item">
        <span class="legend-color" :style="{ background: sc.header }"></span>
        <span class="legend-label">{{ sc.schema }}</span>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && tables.length === 0" description="暂无表数据，请检查连接" class="er-empty" />
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { getTables, getColumns, getForeignKeys, getSchemas } from '@/api/index.js'

const props = defineProps({
  connectionId: { type: [String, Number], required: true }
})

// ======== 响应式状态 ========
const loading = ref(false)
const tables = ref([])
const relationships = ref([])
const selectedTable = ref(null)
const canvasContainer = ref(null)
const svgRef = ref(null)

// 视图变换（平移 + 缩放）
const scale = ref(1)
const viewBoxX = ref(0)
const viewBoxY = ref(0)
const viewBoxW = computed(() => 2000 / scale.value)
const viewBoxH = computed(() => 1500 / scale.value)

// 布局常量
const TABLE_W = 220
const COL_ROW_H = 22
const HDR_H = 32

// Schema 配色方案（8 组颜色循环使用）
const PALETTE = [
  { header: '#409eff', border: '#79bbff' },  // 蓝
  { header: '#67c23a', border: '#95d475' },  // 绿
  { header: '#e6a23c', border: '#eebe77' },  // 橙
  { header: '#f56c6c', border: '#f89898' },  // 红
  { header: '#909399', border: '#b1b3b8' },  // 灰
  { header: '#8b5cf6', border: '#a78bfa' },  // 紫
  { header: '#06b6d4', border: '#67e8f9' },  // 青
  { header: '#ec4899', border: '#f472b6' },  // 粉
]
const schemaColors = ref([])

// ======== 工具函数 ========

/** 计算表总高度（表头 + 所有列行） */
function calcTableH(table) {
  const n = table.columns ? table.columns.length : 0
  return HDR_H + 4 + Math.max(n, 1) * COL_ROW_H + 4
}

/** 判断表是否被选中 */
function isSelected(table) {
  return selectedTable.value && selectedTable.value.name === table.name
}

/** 获取 schema 颜色 */
function schemaClr(schema, type) {
  const found = schemaColors.value.find(s => s.schema === schema)
  if (found) return type === 'header' ? found.header : found.border
  return type === 'header' ? '#409eff' : '#79bbff'
}

/** 构建 schema 颜色映射 */
function buildSchemaColors(list) {
  const schemas = [...new Set(list.map(t => t.schema).filter(Boolean))]
  schemaColors.value = schemas.map((s, i) => ({
    schema: s, ...PALETTE[i % PALETTE.length]
  }))
}

/** 推断关系类型标签 */
function inferRelType(fk) {
  return (fk.is_unique || fk.unique) ? '1:1' : '1:N'
}

/** 获取连线末端 marker（根据关系类型和高亮状态） */
function getLineEndMarker(rel) {
  const hl = rel.highlighted
  if (rel.label === '1:1') return hl ? 'url(#er-one-hl)' : 'url(#er-one)'
  return hl ? 'url(#er-many-hl)' : 'url(#er-many)'
}

// ======== 数据加载 ========
async function fetchDiagramData() {
  if (!props.connectionId) return
  loading.value = true
  tables.value = []
  relationships.value = []
  selectedTable.value = null

  try {
    // 1) 获取所有 schema
    const schemaResp = await getSchemas(props.connectionId)
    const schemas = (schemaResp.data || schemaResp || []).map(s => s.name || s)

    // 2) 遍历 schema 获取表和列信息
    const allTables = []
    for (const schema of schemas) {
      try {
        const tablesResp = await getTables(props.connectionId, schema)
        const rawTables = tablesResp.data || tablesResp || []
        for (const t of rawTables) {
          const tName = t.name || t.table_name || t
          if (String(t.type || 'table').toUpperCase() === 'VIEW') continue

          let cols = []
          try {
            const cResp = await getColumns(props.connectionId, schema, tName)
            cols = (cResp.data || cResp || []).map(c => ({
              name: c.name || c.column_name,
              type: c.data_type || c.type || 'unknown',
              is_pk: !!(c.is_primary_key || c.is_pk || c.column_key === 'PRI')
            }))
          } catch {}
          allTables.push({ name: tName, schema, columns: cols, x: 0, y: 0 })
        }
      } catch {}
    }

    tables.value = allTables
    buildSchemaColors(allTables)
    doAutoLayout()

    // 3) 获取所有外键关系
    const allRels = []
    for (const table of allTables) {
      try {
        const fkResp = await getForeignKeys(props.connectionId, table.schema, table.name)
        const fks = fkResp.data || fkResp || []
        for (const fk of fks) {
          const refT = fk.referred_table || fk.referenced_table_name || fk.referenced_table
          if (!refT) continue
          const src = allTables.find(t => t.name === table.name)
          const tgt = allTables.find(t => t.name === refT)
          if (!src || !tgt) continue
          allRels.push({
            source: table.name, target: refT,
            label: inferRelType(fk), fkData: fk,
            highlighted: false, x1: 0, y1: 0, x2: 0, y2: 0
          })
        }
      } catch {}
    }

    relationships.value = allRels
    refreshLines()
  } catch (err) {
    console.error('加载 ER 图数据失败:', err)
  } finally {
    loading.value = false
  }
}

// ======== 自动布局（网格排列，按 schema 分组） ========
function doAutoLayout() {
  const cols = Math.max(1, Math.ceil(Math.sqrt(tables.value.length)))
  const spX = TABLE_W + 80
  const spY = 260

  const grouped = {}
  for (const t of tables.value) {
    const k = t.schema || 'default'
    if (!grouped[k]) grouped[k] = []
    grouped[k].push(t)
  }

  let gi = 0
  for (const sk of Object.keys(grouped).sort()) {
    for (const t of grouped[sk]) {
      t.x = 60 + (gi % cols) * spX
      t.y = 60 + Math.floor(gi / cols) * spY
      gi++
    }
  }
  nextTick(() => refreshLines())
}

// ======== 更新连线坐标 ========
function refreshLines() {
  for (const rel of relationships.value) {
    const s = tables.value.find(t => t.name === rel.source)
    const t = tables.value.find(t => t.name === rel.target)
    if (!s || !t) continue

    const sH = calcTableH(s), tH = calcTableH(t)
    const sCx = s.x + TABLE_W / 2, sCy = s.y + sH / 2
    const tCx = t.x + TABLE_W / 2, tCy = t.y + tH / 2

    // 根据两表中心的相对方位选择连线出入口
    if (Math.abs(sCx - tCx) > Math.abs(sCy - tCy)) {
      if (sCx < tCx) { rel.x1 = s.x + TABLE_W; rel.y1 = sCy; rel.x2 = t.x; rel.y2 = tCy }
      else            { rel.x1 = s.x;            rel.y1 = sCy; rel.x2 = t.x + TABLE_W; rel.y2 = tCy }
    } else {
      if (sCy < tCy) { rel.x1 = sCx; rel.y1 = s.y + sH; rel.x2 = tCx; rel.y2 = t.y }
      else            { rel.x1 = sCx; rel.y1 = s.y;       rel.x2 = tCx; rel.y2 = t.y + tH }
    }
  }
}

// ======== 画布拖拽平移 ========
let isPanning = false
let panSX = 0, panSY = 0, panVBX = 0, panVBY = 0

function onCanvasMouseDown(e) {
  if (e.button !== 0 || draggingTable) return
  isPanning = true
  panSX = e.clientX; panSY = e.clientY
  panVBX = viewBoxX.value; panVBY = viewBoxY.value
}

function onCanvasMouseMove(e) {
  // 拖拽表
  if (draggingTable) {
    draggingTable.x = dragTX + (e.clientX - dragMX) / scale.value
    draggingTable.y = dragTY + (e.clientY - dragMY) / scale.value
    refreshLines()
    return
  }
  // 平移画布
  if (isPanning) {
    viewBoxX.value = panVBX - (e.clientX - panSX) / scale.value
    viewBoxY.value = panVBY - (e.clientY - panSY) / scale.value
  }
}

function onCanvasMouseUp() {
  isPanning = false
  draggingTable = null
}

// ======== 鼠标滚轮缩放（以鼠标位置为中心） ========
function onCanvasWheel(e) {
  const factor = e.deltaY < 0 ? 1.1 : 0.9
  const newScale = Math.max(0.2, Math.min(3, scale.value * factor))
  const rect = canvasContainer.value.getBoundingClientRect()
  const mx = e.clientX - rect.left, my = e.clientY - rect.top
  const svgX = viewBoxX.value + mx / scale.value
  const svgY = viewBoxY.value + my / scale.value
  scale.value = newScale
  viewBoxX.value = svgX - mx / scale.value
  viewBoxY.value = svgY - my / scale.value
}

function zoomIn()  { scale.value = Math.min(3, scale.value * 1.2) }
function zoomOut() { scale.value = Math.max(0.2, scale.value / 1.2) }
function resetView() { scale.value = 1; viewBoxX.value = 0; viewBoxY.value = 0 }

// ======== 拖拽单个表 ========
let draggingTable = null
let dragMX = 0, dragMY = 0, dragTX = 0, dragTY = 0

function onTableMouseDown(e, table) {
  draggingTable = table
  dragMX = e.clientX; dragMY = e.clientY
  dragTX = table.x;  dragTY = table.y
}

// ======== 点击选中表（高亮相关关系） ========
function onTableClick(table) {
  if (isSelected(table)) {
    selectedTable.value = null
    for (const r of relationships.value) r.highlighted = false
    return
  }
  selectedTable.value = table
  for (const r of relationships.value) {
    r.highlighted = (r.source === table.name || r.target === table.name)
  }
}

// 监听 connectionId 变化，自动重新加载
watch(() => props.connectionId, (v) => {
  if (v) { resetView(); fetchDiagramData() }
}, { immediate: true })
</script>

<style scoped>
.er-diagram-wrapper {
  position: relative; width: 100%; height: 100%;
  display: flex; flex-direction: column;
  background: var(--er-bg, #fafbfc); overflow: hidden;
}
.er-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-bottom: 1px solid var(--er-border, #e4e7ed);
  background: var(--er-toolbar-bg, #fff); z-index: 10; flex-shrink: 0;
}
.er-toolbar-left, .er-toolbar-right { display: flex; align-items: center; gap: 8px; }
.zoom-label { font-size: 12px; color: var(--er-muted, #909399); min-width: 40px; text-align: center; }
.er-canvas-container { flex: 1; overflow: hidden; cursor: grab; user-select: none; }
.er-canvas-container:active { cursor: grabbing; }
.er-svg { display: block; }
.er-table-group { cursor: pointer; }
.er-table-group:hover .er-table-body { filter: brightness(0.97); }
.er-col-row:hover { fill: rgba(64, 158, 255, 0.06); }
.er-legend {
  position: absolute; bottom: 12px; left: 12px;
  background: var(--er-legend-bg, rgba(255,255,255,0.95));
  border: 1px solid var(--er-border, #e4e7ed); border-radius: 6px;
  padding: 8px 12px; font-size: 12px; z-index: 10;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.legend-title { font-weight: 600; color: var(--er-text, #303133); margin-bottom: 6px; }
.legend-item { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.legend-color { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
.legend-label { color: var(--er-text-secondary, #606266); }
.er-empty { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }

/* 暗色模式 CSS 变量覆盖 */
:global(html.dark) .er-diagram-wrapper {
  --er-bg: #141414; --er-border: #363636;
  --er-toolbar-bg: #1d1e1f; --er-muted: #8b8b8b;
  --er-legend-bg: rgba(29,30,31,0.95);
  --er-text: #e5eaf3; --er-text-secondary: #cfd3dc;
}
</style>
