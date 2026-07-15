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
          </span>
        </template>
      </el-tree>
      <el-empty v-if="!treeLoading && treeData.length === 0" description="No schemas found" :image-size="80" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getSchemas, getTables, getColumns, getIndexes, getForeignKeys } from '@/api/index.js'

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
        }
      ]

      resolve(children)
    } catch (error) {
      console.error('Failed to load tables:', error)
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
    case 'folder': return data.folderType === 'views' ? 'View' : 'Grid'
    case 'table': return 'Grid'
    case 'view': return 'View'
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
