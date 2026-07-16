<template>
  <div class="db-tree-container">
    <div class="tree-search">
      <el-input
        v-model="filterText"
        placeholder="Search tables..."
        clearable
        size="small"
        prefix-icon="Search"
      />
    </div>
    <div class="tree-content" v-loading="treeLoading">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        node-key="nodeId"
        :filter-node-method="filterNode"
        @node-click="handleNodeClick"
        lazy
        :load="loadNode"
        highlight-current
        :expand-on-click-node="false"
      >
        <template #default="{ node, data }">
          <el-tooltip
            :content="getNodeTooltip(data)"
            placement="right"
            :disabled="!shouldShowTooltip(data)"
            :show-after="500"
          >
            <span class="tree-node">
              <el-icon :size="14" class="node-icon">
                <component :is="getNodeIcon(data)" />
              </el-icon>
              <span class="node-label">{{ data.label }}</span>
              <el-tag v-if="data.type === 'table'" size="small" type="info" class="node-badge">
                T
              </el-tag>
              <el-tag v-else-if="data.type === 'view'" size="small" type="warning" class="node-badge">
                V
              </el-tag>
              <el-tag v-else-if="data.type === 'procedure'" size="small" type="success" class="node-badge">
                P
              </el-tag>
              <el-tag v-else-if="data.type === 'trigger'" size="small" type="danger" class="node-badge">
                Tr
              </el-tag>
              <el-tag v-else-if="data.type === 'function'" size="small" class="node-badge">
                F
              </el-tag>
              <el-tag v-else-if="data.type === 'sequence'" size="small" type="info" class="node-badge">
                Sq
              </el-tag>
              <el-tag
                v-else-if="data.type === 'folder' && data.count !== null && data.count !== undefined"
                size="small"
                type="info"
                round
                class="node-badge"
              >
                {{ data.count }}
              </el-tag>
            </span>
          </el-tooltip>
        </template>
      </el-tree>
      <el-empty v-if="!treeLoading && treeData.length === 0" description="No schemas found" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getSchemas, getTables, getColumns, getIndexes, getForeignKeys, getProcedures, getTriggers, getFunctions, getSequences } from '@/api/index.js'

const props = defineProps({
  connectionId: { type: [String, Number], default: null }
})

const emit = defineEmits(['node-select'])

const treeRef = ref(null)
const filterText = ref('')
const treeLoading = ref(false)
const treeData = ref([])

const treeProps = {
  label: 'label',
  children: 'children',
  isLeaf: 'isLeaf'
}

watch(filterText, (val) => {
  treeRef.value?.filter(val)
})

watch(() => props.connectionId, async (newVal) => {
  if (newVal) {
    await loadTreeRoot()
  } else {
    treeData.value = []
  }
}, { immediate: true })

async function loadTreeRoot() {
  if (!props.connectionId) return
  treeLoading.value = true
  treeData.value = []
  try {
    const response = await getSchemas(props.connectionId)
    const schemas = response.data || response || []
    treeData.value = schemas.map(schema => ({
      nodeId: `schema_${schema.name || schema}`,
      label: schema.name || schema,
      type: 'schema',
      schema: schema.name || schema,
      isLeaf: false,
      children: undefined
    }))
  } catch (error) {
    console.error('Failed to load schemas:', error)
    treeData.value = []
  } finally {
    treeLoading.value = false
  }
}

async function loadNode(node, resolve) {
  const data = node.data

  if (node.level === 0) {
    return resolve([])
  }

  if (data.type === 'schema') {
    try {
      const response = await getTables(props.connectionId, data.schema)
      const tables = response.data || response || []

      const tableNodes = tables.map(table => {
        const tableName = table.name || table.table_name || table
        const tableType = table.type || 'table'
        return {
          nodeId: `table_${data.schema}_${tableName}`,
          label: tableName,
          type: tableType === 'VIEW' ? 'view' : 'table',
          schema: data.schema,
          tableName: tableName,
          isLeaf: false,
          children: undefined
        }
      })

      // Add virtual folders for organization
      const children = [
        {
          nodeId: `folder_tables_${data.schema}`,
          label: 'Tables',
          type: 'folder',
          folderType: 'tables',
          schema: data.schema,
          isLeaf: tableNodes.filter(n => n.type === 'table').length === 0,
          children: tableNodes.filter(n => n.type === 'table'),
          loaded: true
        },
        {
          nodeId: `folder_views_${data.schema}`,
          label: 'Views',
          type: 'folder',
          folderType: 'views',
          schema: data.schema,
          isLeaf: tableNodes.filter(n => n.type === 'view').length === 0,
          children: tableNodes.filter(n => n.type === 'view'),
          loaded: true
        },
        {
          nodeId: `folder_procedures_${data.schema}`,
          label: 'Procedures',
          type: 'folder',
          folderType: 'procedures',
          schema: data.schema,
          isLeaf: false,
          loaded: false,
          count: null
        },
        {
          nodeId: `folder_triggers_${data.schema}`,
          label: 'Triggers',
          type: 'folder',
          folderType: 'triggers',
          schema: data.schema,
          isLeaf: false,
          loaded: false,
          count: null
        },
        {
          nodeId: `folder_functions_${data.schema}`,
          label: 'Functions',
          type: 'folder',
          folderType: 'functions',
          schema: data.schema,
          isLeaf: false,
          loaded: false,
          count: null
        },
        {
          nodeId: `folder_sequences_${data.schema}`,
          label: 'Sequences',
          type: 'folder',
          folderType: 'sequences',
          schema: data.schema,
          isLeaf: false,
          loaded: false,
          count: null
        }
      ]

      resolve(children)
    } catch (error) {
      console.error('Failed to load tables:', error)
      resolve([])
    }
  } else if (data.type === 'folder' && !data.loaded) {
    // Lazy load procedures, triggers, functions, sequences
    try {
      let items = []
      let itemType = 'item'
      const fetchMap = {
        procedures: { fn: getProcedures, type: 'procedure' },
        triggers: { fn: getTriggers, type: 'trigger' },
        functions: { fn: getFunctions, type: 'function' },
        sequences: { fn: getSequences, type: 'sequence' }
      }
      const config = fetchMap[data.folderType]
      if (config) {
        const response = await config.fn(props.connectionId, data.schema)
        items = response.data || response || []
        itemType = config.type
      }

      // Update count and loaded state on the node data
      data.count = items.length
      data.loaded = true
      data.isLeaf = items.length === 0

      const childNodes = items.map((item, index) => {
        const itemName = item.name || item.procedure_name || item.trigger_name || item.function_name || item.sequence_name || `item_${index}`
        return {
          nodeId: `${data.folderType}_${data.schema}_${itemName}`,
          label: itemName,
          type: itemType,
          schema: data.schema,
          itemData: item,
          isLeaf: true
        }
      })

      resolve(childNodes)
    } catch (error) {
      console.error(`Failed to load ${data.folderType}:`, error)
      data.loaded = true
      data.count = 0
      data.isLeaf = true
      resolve([])
    }
  } else if (data.type === 'table' || data.type === 'view') {
    try {
      const children = [
        {
          nodeId: `sub_columns_${data.schema}_${data.tableName}`,
          label: 'Columns',
          type: 'subfolder',
          subType: 'columns',
          schema: data.schema,
          tableName: data.tableName,
          isLeaf: false
        },
        {
          nodeId: `sub_indexes_${data.schema}_${data.tableName}`,
          label: 'Indexes',
          type: 'subfolder',
          subType: 'indexes',
          schema: data.schema,
          tableName: data.tableName,
          isLeaf: false
        },
        {
          nodeId: `sub_fks_${data.schema}_${data.tableName}`,
          label: 'Foreign Keys',
          type: 'subfolder',
          subType: 'foreign_keys',
          schema: data.schema,
          tableName: data.tableName,
          isLeaf: false
        }
      ]
      resolve(children)
    } catch (error) {
      resolve([])
    }
  } else if (data.type === 'subfolder') {
    try {
      let items = []
      if (data.subType === 'columns') {
        const response = await getColumns(props.connectionId, data.schema, data.tableName)
        items = (response.data || response || []).map(col => ({
          nodeId: `col_${data.schema}_${data.tableName}_${col.name || col.column_name}`,
          label: `${col.name || col.column_name} (${col.data_type || col.type || 'unknown'})`,
          type: 'column',
          schema: data.schema,
          tableName: data.tableName,
          columnData: col,
          isLeaf: true
        }))
      } else if (data.subType === 'indexes') {
        const response = await getIndexes(props.connectionId, data.schema, data.tableName)
        items = (response.data || response || []).map(idx => ({
          nodeId: `idx_${data.schema}_${data.tableName}_${idx.name || idx.index_name}`,
          label: idx.name || idx.index_name || 'index',
          type: 'index',
          schema: data.schema,
          tableName: data.tableName,
          indexData: idx,
          isLeaf: true
        }))
      } else if (data.subType === 'foreign_keys') {
        const response = await getForeignKeys(props.connectionId, data.schema, data.tableName)
        items = (response.data || response || []).map(fk => ({
          nodeId: `fk_${data.schema}_${data.tableName}_${fk.name || fk.constraint_name || Math.random()}`,
          label: fk.name || fk.constraint_name || 'FK',
          type: 'foreign_key',
          schema: data.schema,
          tableName: data.tableName,
          fkData: fk,
          isLeaf: true
        }))
      }
      resolve(items)
    } catch (error) {
      console.error('Failed to load sub-items:', error)
      resolve([])
    }
  } else {
    resolve([])
  }
}

function filterNode(value, data) {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

function handleNodeClick(data) {
  emit('node-select', {
    type: data.type,
    schema: data.schema,
    tableName: data.tableName,
    label: data.label,
    rawData: data
  })
}

function getNodeIcon(data) {
  switch (data.type) {
    case 'schema': return 'FolderOpened'
    case 'folder':
      if (data.folderType === 'views') return 'View'
      if (data.folderType === 'procedures') return 'SetUp'
      if (data.folderType === 'triggers') return 'Bell'
      if (data.folderType === 'functions') return 'Cpu'
      if (data.folderType === 'sequences') return 'Sort'
      return 'Grid'
    case 'table': return 'Grid'
    case 'view': return 'View'
    case 'procedure': return 'SetUp'
    case 'trigger': return 'Bell'
    case 'function': return 'Cpu'
    case 'sequence': return 'Sort'
    case 'subfolder':
      if (data.subType === 'columns') return 'List'
      if (data.subType === 'indexes') return 'Key'
      if (data.subType === 'foreign_keys') return 'Link'
      return 'Folder'
    case 'column': return 'Minus'
    case 'index': return 'Key'
    case 'foreign_key': return 'Link'
    default: return 'Document'
  }
}

function shouldShowTooltip(data) {
  return ['procedure', 'trigger', 'function', 'sequence', 'table', 'view'].includes(data.type)
}

function getNodeTooltip(data) {
  if (!shouldShowTooltip(data)) return ''
  const parts = [`Type: ${data.type}`]
  if (data.schema) parts.push(`Schema: ${data.schema}`)
  if (data.tableName) parts.push(`Table: ${data.tableName}`)
  if (data.itemData) {
    const item = data.itemData
    if (item.definition || item.routine_definition || item.trigger_body) {
      const def = item.definition || item.routine_definition || item.trigger_body
      parts.push(def.length > 120 ? def.substring(0, 120) + '...' : def)
    }
    if (item.language) parts.push(`Language: ${item.language}`)
    if (item.return_type || item.data_type) parts.push(`Returns: ${item.return_type || item.data_type}`)
  }
  return parts.join(' | ')
}

function refresh() {
  loadTreeRoot()
}

defineExpose({ refresh })
</script>

<style scoped>
.db-tree-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tree-search {
  padding: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.tree-content {
  flex: 1;
  overflow: auto;
  padding: 4px 0;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  width: 100%;
}

.node-icon {
  color: #909399;
  flex-shrink: 0;
}

.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-badge {
  margin-left: auto;
  flex-shrink: 0;
  transform: scale(0.85);
}
</style>
