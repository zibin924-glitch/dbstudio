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

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'sql' },
  readOnly: { type: Boolean, default: false },
  height: { type: String, default: '100%' }
})

const emit = defineEmits(['update:modelValue', 'execute'])

const editorContainer = ref(null)
let editor = null
let isUpdatingFromProp = false

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
