<template>
  <div class="explain-plan-wrapper">
    <!-- 工具栏 -->
    <div class="explain-toolbar">
      <span class="explain-title">
        <el-icon><TrendCharts /></el-icon>
        执行计划 (EXPLAIN)
      </span>
      <div class="explain-toolbar-right">
        <el-tag v-if="totalCost" size="small" :type="totalCost > 1000 ? 'danger' : 'success'">
          总代价: {{ totalCost.toFixed(1) }}
        </el-tag>
        <el-button size="small" text @click="toggleView">
          {{ viewMode === 'tree' ? '文本视图' : '树形视图' }}
        </el-button>
      </div>
    </div>

    <!-- 树形视图 -->
    <div v-if="viewMode === 'tree'" class="explain-tree-view" v-loading="loading">
      <template v-if="planNodes.length > 0">
        <div class="plan-tree">
          <PlanNode
            v-for="(node, idx) in planNodes"
            :key="idx"
            :node="node"
            :max-cost="maxCost"
            :depth="0"
          />
        </div>
      </template>
      <el-empty v-else description="无法解析执行计划" />
    </div>

    <!-- 文本视图 -->
    <div v-else class="explain-text-view" v-loading="loading">
      <pre class="explain-raw-text">{{ rawText }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, h, defineComponent } from 'vue'
import { executeQuery } from '@/api/index.js'

const props = defineProps({
  connectionId: { type: [String, Number], required: true },
  sql: { type: String, required: true },
  dbType: { type: String, default: 'mysql' },
  analyze: { type: Boolean, default: false }
})

const loading = ref(false)
const rawText = ref('')
const planNodes = ref([])
const viewMode = ref('tree')

// 计算最大代价（用于颜色映射）
const maxCost = computed(() => {
  let max = 0
  function walk(nodes) {
    for (const n of nodes) {
      if (n.cost > max) max = n.cost
      if (n.children) walk(n.children)
    }
  }
  walk(planNodes.value)
  return max || 1
})

// 总代价
const totalCost = computed(() => {
  if (planNodes.value.length > 0) return planNodes.value[0].cost
  return 0
})

function toggleView() {
  viewMode.value = viewMode.value === 'tree' ? 'text' : 'tree'
}

// ======== 执行 EXPLAIN ========
async function runExplain() {
  if (!props.connectionId || !props.sql) return
  loading.value = true
  rawText.value = ''
  planNodes.value = []

  try {
    // 构造 EXPLAIN SQL
    let explainSql
    const dbType = (props.dbType || 'mysql').toLowerCase()
    if (dbType === 'postgresql' || dbType === 'postgres') {
      explainSql = props.analyze
        ? `EXPLAIN (ANALYZE, FORMAT JSON) ${props.sql}`
        : `EXPLAIN (FORMAT JSON) ${props.sql}`
    } else {
      explainSql = props.analyze
        ? `EXPLAIN ANALYZE ${props.sql}`
        : `EXPLAIN ${props.sql}`
    }

    const resp = await executeQuery({
      connection_id: props.connectionId,
      sql: explainSql,
      page: 1,
      page_size: 1000
    })
    const data = resp.data || resp
    const rows = data.rows || []
    const columns = data.columns || []

    // 拼接原始文本
    rawText.value = rows.map(r => {
      if (Array.isArray(r)) return r.join(' | ')
      return Object.values(r).join(' | ')
    }).join('\n')

    // 尝试解析为树结构
    if (dbType === 'postgresql' || dbType === 'postgres') {
      planNodes.value = parsePostgresPlan(rows, columns)
    } else {
      planNodes.value = parseMysqlPlan(rows, columns)
    }
  } catch (err) {
    console.error('EXPLAIN 执行失败:', err)
    rawText.value = '执行失败: ' + (err.response?.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}

// ======== MySQL EXPLAIN 解析 ========
function parseMysqlPlan(rows, columns) {
  if (!rows || rows.length === 0) return []

  // 获取列名（可能是数组或对象）
  const colNames = columns.map(c => (c.name || c.label || c).toString().toLowerCase())
  const idIdx = colNames.indexOf('id')
  const typeIdx = colNames.indexOf('type')
  const tableIdx = colNames.indexOf('table')
  const rowsIdx = colNames.indexOf('rows')
  const filteredIdx = colNames.indexOf('filtered')
  const extraIdx = colNames.indexOf('extra')
  const possibleKeysIdx = colNames.indexOf('possible_keys')
  const keyIdx = colNames.indexOf('key')
  const keyLenIdx = colNames.indexOf('key_len')
  const refIdx = colNames.indexOf('ref')

  const nodes = rows.map((row, i) => {
    const vals = Array.isArray(row) ? row : Object.values(row)
    return {
      id: idIdx >= 0 ? vals[idIdx] : i,
      operation: typeIdx >= 0 ? vals[typeIdx] : 'UNKNOWN',
      table: tableIdx >= 0 ? vals[tableIdx] : '-',
      estimatedRows: rowsIdx >= 0 ? Number(vals[rowsIdx]) || 0 : 0,
      cost: rowsIdx >= 0 ? Number(vals[rowsIdx]) || 0 : 0,
      actualTime: null,
      filtered: filteredIdx >= 0 ? vals[filteredIdx] : null,
      extra: extraIdx >= 0 ? vals[extraIdx] : '',
      possibleKeys: possibleKeysIdx >= 0 ? vals[possibleKeysIdx] : null,
      key: keyIdx >= 0 ? vals[keyIdx] : null,
      keyLen: keyLenIdx >= 0 ? vals[keyLenIdx] : null,
      ref: refIdx >= 0 ? vals[refIdx] : null,
      children: [],
      _sortId: idIdx >= 0 ? Number(vals[idIdx]) || 0 : 0
    }
  })

  // 按 id 构建层级（简单处理：相同 id 为兄弟，id 递增为子节点）
  if (nodes.length <= 1) return nodes
  const root = [nodes[0]]
  let currentParent = nodes[0]
  for (let i = 1; i < nodes.length; i++) {
    if (nodes[i]._sortId > currentParent._sortId) {
      currentParent.children.push(nodes[i])
    } else {
      root.push(nodes[i])
      currentParent = nodes[i]
    }
  }
  return root
}

// ======== PostgreSQL EXPLAIN (JSON) 解析 ========
function parsePostgresPlan(rows, columns) {
  if (!rows || rows.length === 0) return []

  try {
    // PostgreSQL JSON 格式：第一行第一列是 JSON 字符串
    const vals = Array.isArray(rows[0]) ? rows[0] : Object.values(rows[0])
    let jsonStr = vals[0]

    // 如果多行拼接
    if (rows.length > 1) {
      jsonStr = rows.map(r => {
        const v = Array.isArray(r) ? r[0] : Object.values(r)[0]
        return v
      }).join('')
    }

    const parsed = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr
    const plan = parsed[0]?.Plan || parsed.Plan || parsed

    function walkNode(node) {
      const result = {
        operation: node['Node Type'] || 'UNKNOWN',
        table: node['Relation Name'] || node['Alias'] || '',
        estimatedRows: node['Plan Rows'] || 0,
        cost: node['Total Cost'] || 0,
        actualTime: node['Actual Total Time'] || null,
        startupCost: node['Startup Cost'] || 0,
        actualRows: node['Actual Rows'] || null,
        loops: node['Actual Loops'] || null,
        filter: node['Filter'] || null,
        indexName: node['Index Name'] || null,
        joinType: node['Join Type'] || null,
        strategy: node['Strategy'] || null,
        children: []
      }
      if (node.Plans) {
        result.children = node.Plans.map(walkNode)
      }
      return result
    }

    return [walkNode(plan)]
  } catch (err) {
    console.warn('PostgreSQL EXPLAIN JSON 解析失败，使用文本模式:', err)
    return []
  }
}

// ======== PlanNode 递归组件（渲染单个节点） ========
const PlanNode = defineComponent({
  name: 'PlanNode',
  props: {
    node: { type: Object, required: true },
    maxCost: { type: Number, default: 1 },
    depth: { type: Number, default: 0 }
  },
  setup(props) {
    // 根据代价计算颜色（绿 -> 黄 -> 红）
    function costColor(cost) {
      const ratio = Math.min(cost / (props.maxCost || 1), 1)
      if (ratio < 0.3) return '#67c23a'
      if (ratio < 0.7) return '#e6a23c'
      return '#f56c6c'
    }

    return () => {
      const n = props.node
      const indent = props.depth * 24

      // 构造详情列表
      const details = []
      if (n.table) details.push(`表: ${n.table}`)
      if (n.estimatedRows) details.push(`预估行数: ${n.estimatedRows}`)
      if (n.actualRows != null) details.push(`实际行数: ${n.actualRows}`)
      if (n.cost) details.push(`代价: ${n.cost.toFixed(1)}`)
      if (n.actualTime != null) details.push(`实际耗时: ${n.actualTime}ms`)
      if (n.key) details.push(`索引: ${n.key}`)
      if (n.indexName) details.push(`索引: ${n.indexName}`)
      if (n.filtered != null) details.push(`过滤率: ${n.filtered}%`)
      if (n.extra) details.push(`额外: ${n.extra}`)
      if (n.filter) details.push(`过滤条件: ${n.filter}`)
      if (n.joinType) details.push(`连接类型: ${n.joinType}`)
      if (n.strategy) details.push(`策略: ${n.strategy}`)

      const nodeEl = h('div', {
        class: 'plan-node',
        style: { marginLeft: indent + 'px' },
        title: details.join('\n')
      }, [
        h('div', { class: 'plan-node-header' }, [
          h('span', {
            class: 'plan-node-badge',
            style: { backgroundColor: costColor(n.cost) }
          }, n.operation),
          n.table ? h('span', { class: 'plan-node-table' }, n.table) : null,
          h('span', { class: 'plan-node-rows' },
            n.estimatedRows ? `~${n.estimatedRows} rows` : ''
          ),
          h('span', { class: 'plan-node-cost', style: { color: costColor(n.cost) } },
            n.cost ? `cost: ${n.cost.toFixed(1)}` : ''
          ),
          n.actualTime != null
            ? h('span', { class: 'plan-node-time' }, `${n.actualTime}ms`)
            : null
        ]),
        // 详情（折叠显示在 tooltip，这里用额外信息行）
        details.length > 0
          ? h('div', { class: 'plan-node-details' }, details.slice(0, 3).join(' | '))
          : null
      ])

      // 递归子节点
      const childEls = (n.children || []).map((child, ci) =>
        h(PlanNode, { key: ci, node: child, maxCost: props.maxCost, depth: props.depth + 1 })
      )

      return h('div', { class: 'plan-node-wrapper' }, [nodeEl, ...childEls])
    }
  }
})

// 监听属性变化自动执行
watch(
  () => [props.connectionId, props.sql, props.analyze],
  () => { if (props.connectionId && props.sql) runExplain() },
  { immediate: true }
)
</script>

<style scoped>
.explain-plan-wrapper {
  display: flex; flex-direction: column;
  height: 100%; background: var(--ep-bg, #fff);
  overflow: hidden;
}
.explain-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ep-border, #e4e7ed);
  background: var(--ep-toolbar-bg, #fafafa);
  flex-shrink: 0;
}
.explain-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 600; color: var(--ep-text, #303133);
}
.explain-toolbar-right { display: flex; align-items: center; gap: 8px; }

/* 树形视图 */
.explain-tree-view {
  flex: 1; overflow: auto; padding: 12px 16px;
}
.plan-tree { display: flex; flex-direction: column; gap: 2px; }

.plan-node-wrapper { display: flex; flex-direction: column; gap: 2px; }

.plan-node {
  border: 1px solid var(--ep-border, #e4e7ed);
  border-radius: 6px; padding: 6px 10px;
  background: var(--ep-node-bg, #f9fafb);
  transition: all 0.15s;
  cursor: default;
}
.plan-node:hover {
  border-color: #409eff;
  box-shadow: 0 1px 4px rgba(64, 158, 255, 0.15);
}
.plan-node-header {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.plan-node-badge {
  display: inline-block; padding: 1px 8px; border-radius: 4px;
  color: #fff; font-size: 11px; font-weight: 600;
  white-space: nowrap;
}
.plan-node-table {
  font-size: 12px; font-weight: 600; color: var(--ep-text, #303133);
}
.plan-node-rows {
  font-size: 11px; color: var(--ep-muted, #909399);
}
.plan-node-cost {
  font-size: 11px; font-weight: 500;
}
.plan-node-time {
  font-size: 11px; color: #e6a23c; font-weight: 500;
}
.plan-node-details {
  font-size: 11px; color: var(--ep-muted, #909399);
  margin-top: 4px; padding-top: 4px;
  border-top: 1px dashed var(--ep-border, #e4e7ed);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* 文本视图 */
.explain-text-view { flex: 1; overflow: auto; padding: 12px 16px; }
.explain-raw-text {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px; line-height: 1.6;
  color: var(--ep-text, #303133);
  white-space: pre-wrap; word-break: break-all;
  background: var(--ep-node-bg, #f9fafb);
  padding: 12px; border-radius: 6px;
  border: 1px solid var(--ep-border, #e4e7ed);
}

/* 暗色模式 */
:global(html.dark) .explain-plan-wrapper {
  --ep-bg: #141414; --ep-border: #363636;
  --ep-toolbar-bg: #1d1e1f; --ep-text: #e5eaf3;
  --ep-muted: #8b8b8b; --ep-node-bg: #1d1e1f;
}
</style>
