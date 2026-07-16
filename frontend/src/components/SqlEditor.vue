<template>
  <div class="sql-editor-container">
    <div class="editor-toolbar">
      <el-button-group>
        <el-button size="small" @click="handleExecute" type="primary" plain>
          <el-icon><CaretRight /></el-icon>
          Execute
        </el-button>
        <el-button size="small" @click="handleFormat" plain>
          <el-icon><Document /></el-icon>
          Format
        </el-button>
      </el-button-group>
      <div class="toolbar-right">
        <el-tag size="small" type="info">Ctrl+Enter to run</el-tag>
      </div>
    </div>
    <div ref="editorContainer" class="editor-wrapper"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { useConnectionStore } from '@/stores/connection.js'
import { getTables, getColumns } from '@/api/index.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'sql' },
  readOnly: { type: Boolean, default: false },
  height: { type: String, default: '100%' },
  connectionId: { type: [String, Number], default: null }
})

const emit = defineEmits(['update:modelValue', 'execute'])

const editorContainer = ref(null)
const connectionStore = useConnectionStore()
let editor = null
let isUpdatingFromProp = false
let completionProviderDisposable = null

// ---- Schema cache for auto-completion ----
const schemaCache = ref({
  tables: [],           // Array of table name strings
  columnsByTable: {}    // { tableName: [ { name, data_type }, ... ] }
})
let tablesFetchPromise = null
const columnFetchPromises = {}

function getCurrentConnectionId() {
  return props.connectionId || connectionStore.currentConnection?.id || null
}

async function fetchTables() {
  const connId = getCurrentConnectionId()
  if (!connId) return []
  // Return cached if available
  if (schemaCache.value.tables.length > 0) return schemaCache.value.tables
  // Deduplicate concurrent requests
  if (tablesFetchPromise) return tablesFetchPromise
  tablesFetchPromise = (async () => {
    try {
      const resp = await getTables(connId)
      const tables = (resp.data || resp || []).map(t => typeof t === 'string' ? t : (t.table_name || t.name || ''))
      schemaCache.value.tables = tables.filter(Boolean)
      return schemaCache.value.tables
    } catch {
      return []
    } finally {
      tablesFetchPromise = null
    }
  })()
  return tablesFetchPromise
}

async function fetchColumnsForTable(tableName) {
  const connId = getCurrentConnectionId()
  if (!connId) return []
  const cacheKey = tableName.toLowerCase()
  if (schemaCache.value.columnsByTable[cacheKey]) {
    return schemaCache.value.columnsByTable[cacheKey]
  }
  if (columnFetchPromises[cacheKey]) return columnFetchPromises[cacheKey]
  columnFetchPromises[cacheKey] = (async () => {
    try {
      const resp = await getColumns(connId, null, tableName)
      const cols = (resp.data || resp || []).map(c => ({
        name: c.column_name || c.name || '',
        data_type: c.data_type || c.type || ''
      }))
      schemaCache.value.columnsByTable[cacheKey] = cols.filter(c => c.name)
      return schemaCache.value.columnsByTable[cacheKey]
    } catch {
      return []
    } finally {
      delete columnFetchPromises[cacheKey]
    }
  })()
  return columnFetchPromises[cacheKey]
}

// Clear cache when connection changes
watch(() => props.connectionId, () => {
  schemaCache.value = { tables: [], columnsByTable: {} }
})

// SQL keywords that suggest a table or column reference follows
const SQL_CONTEXT_KEYWORDS = /\b(SELECT|FROM|WHERE|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN|ON|SET|INTO|UPDATE|BY|HAVING|AND|OR|NOT\s+IN|IN|EXISTS|BETWEEN|AS)\s*$/i

function getSqlContext(model, position) {
  const textUntilPosition = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: 1,
    endLineNumber: position.lineNumber,
    endColumn: position.column
  })

  // Check if we're after a dot (table.column)
  const dotMatch = textUntilPosition.match(/(\w+)\.\s*(\w*)$/)
  if (dotMatch) {
    return { type: 'column', tableName: dotMatch[1], prefix: dotMatch[2] || '' }
  }

  // Check if the preceding token is a SQL keyword that expects a table/column
  const keywordMatch = textUntilPosition.match(SQL_CONTEXT_KEYWORDS)
  if (keywordMatch) {
    const word = textUntilPosition.match(/(\w*)$/)
    return { type: 'table_or_column', prefix: word ? word[1] : '' }
  }

  // Generic: provide suggestions if typing a word
  const genericWord = textUntilPosition.match(/(\w+)$/)
  if (genericWord) {
    return { type: 'generic', prefix: genericWord[1] }
  }

  return null
}

// Extract table names referenced in the current SQL (for column suggestions)
function extractTablesFromSql(sql) {
  const tables = new Set()
  // FROM/JOIN <table>
  const fromJoinRegex = /(?:FROM|JOIN)\s+(\w+)/gi
  let m
  while ((m = fromJoinRegex.exec(sql)) !== null) {
    tables.add(m[1])
  }
  return Array.from(tables)
}

function createCompletionProvider() {
  return {
    triggerCharacters: ['.', ' '],
    provideCompletionItems: async (model, position) => {
      const connId = getCurrentConnectionId()
      if (!connId) return { suggestions: [] }

      const ctx = getSqlContext(model, position)
      if (!ctx) return { suggestions: [] }

      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn
      }

      const suggestions = []

      if (ctx.type === 'column' && ctx.tableName) {
        // Dot notation: fetch columns for the specific table
        const cols = await fetchColumnsForTable(ctx.tableName)
        for (const col of cols) {
          suggestions.push({
            label: col.name,
            kind: monaco.languages.CompletionItemKind.Field,
            detail: col.data_type || 'column',
            insertText: col.name,
            range
          })
        }
      } else if (ctx.type === 'table_or_column') {
        // After SQL keyword: suggest tables and columns from referenced tables
        const tables = await fetchTables()
        for (const tbl of tables) {
          suggestions.push({
            label: tbl,
            kind: monaco.languages.CompletionItemKind.Class,
            detail: 'table',
            insertText: tbl,
            range
          })
        }
        // Also suggest columns from tables already mentioned in the SQL
        const fullSql = model.getValue()
        const referencedTables = extractTablesFromSql(fullSql)
        for (const tbl of referencedTables) {
          const cols = await fetchColumnsForTable(tbl)
          for (const col of cols) {
            suggestions.push({
              label: col.name,
              kind: monaco.languages.CompletionItemKind.Field,
              detail: `${col.data_type || 'column'} (${tbl})`,
              insertText: col.name,
              range
            })
          }
        }
      } else if (ctx.type === 'generic') {
        // Generic word being typed: provide tables and SQL keywords
        const tables = await fetchTables()
        for (const tbl of tables) {
          suggestions.push({
            label: tbl,
            kind: monaco.languages.CompletionItemKind.Class,
            detail: 'table',
            insertText: tbl,
            range
          })
        }
      }

      return { suggestions }
    }
  }
}

onMounted(() => {
  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue || '',
    language: props.language,
    theme: 'vs',
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    tabSize: 2,
    renderWhitespace: 'selection',
    bracketPairColorization: { enabled: true },
    suggestOnTriggerCharacters: true,
    quickSuggestions: true,
    padding: { top: 8, bottom: 8 },
    scrollbar: {
      verticalScrollbarSize: 8,
      horizontalScrollbarSize: 8
    }
  })

  // Register SQL completion provider
  completionProviderDisposable = monaco.languages.registerCompletionItemProvider(
    'sql',
    createCompletionProvider()
  )

  // Listen for content changes
  editor.onDidChangeModelContent(() => {
    const value = editor.getValue()
    if (!isUpdatingFromProp) {
      emit('update:modelValue', value)
    }
  })

  // Add Ctrl+Enter keybinding for execute
  editor.addAction({
    id: 'execute-query',
    label: 'Execute Query',
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
    run: () => {
      handleExecute()
    }
  })

  // Add Ctrl+Shift+F for format
  editor.addAction({
    id: 'format-sql',
    label: 'Format SQL',
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF],
    run: () => {
      handleFormat()
    }
  })
})

watch(() => props.modelValue, (newVal) => {
  if (editor && newVal !== editor.getValue()) {
    isUpdatingFromProp = true
    editor.setValue(newVal || '')
    isUpdatingFromProp = false
  }
})

watch(() => props.readOnly, (newVal) => {
  if (editor) {
    editor.updateOptions({ readOnly: newVal })
  }
})

onBeforeUnmount(() => {
  if (completionProviderDisposable) {
    completionProviderDisposable.dispose()
    completionProviderDisposable = null
  }
  if (editor) {
    editor.dispose()
    editor = null
  }
})

function handleExecute() {
  const selection = editor.getSelection()
  const selectedText = editor.getModel().getValueInRange(selection)
  const sql = selectedText || editor.getValue()
  emit('execute', sql.trim())
}

function handleFormat() {
  if (!editor) return
  let sql = editor.getValue()

  // Simple client-side SQL formatting
  sql = formatSql(sql)

  isUpdatingFromProp = true
  editor.setValue(sql)
  isUpdatingFromProp = false
  emit('update:modelValue', sql)
}

function formatSql(sql) {
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'INSERT', 'INTO', 'VALUES',
    'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'ALTER', 'DROP', 'INDEX',
    'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'ON',
    'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL',
    'AS', 'IN', 'NOT', 'NULL', 'IS', 'LIKE', 'BETWEEN', 'EXISTS',
    'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'ASC', 'DESC'
  ]

  let formatted = sql
  // Uppercase keywords
  for (const kw of keywords) {
    const regex = new RegExp(`\\b${kw}\\b`, 'gi')
    formatted = formatted.replace(regex, kw)
  }

  // Add newlines before major clauses
  const majorKeywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN', 'FULL JOIN', 'CROSS JOIN', 'UNION', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE']

  for (const kw of majorKeywords) {
    const regex = new RegExp(`\\s+(${kw})\\b`, 'gi')
    if (['AND', 'OR'].includes(kw)) {
      formatted = formatted.replace(regex, `\n    ${kw}`)
    } else {
      formatted = formatted.replace(regex, `\n${kw}`)
    }
  }

  return formatted.trim()
}

function getEditorValue() {
  return editor ? editor.getValue() : ''
}

function focus() {
  editor?.focus()
}

defineExpose({ getEditorValue, focus })
</script>

<style scoped>
.sql-editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-wrapper {
  flex: 1;
  min-height: 150px;
}
</style>
