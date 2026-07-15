<template>
  <div class="generator-page">
    <div class="page-header">
      <h2 class="page-title">Generator</h2>
    </div>

    <!-- Connection & Table Selection -->
    <div class="selection-panel">
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="selection-group">
            <label class="selection-label">Connection</label>
            <el-select
              v-model="selectedConnectionId"
              placeholder="Select connection"
              filterable
              style="width: 100%;"
              @change="onConnectionChange"
            >
              <el-option
                v-for="conn in connectionStore.connections"
                :key="conn.id"
                :label="`${conn.name} (${conn.db_type})`"
                :value="conn.id"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="selection-group">
            <label class="selection-label">Schema</label>
            <el-select
              v-model="selectedSchema"
              placeholder="Select schema"
              filterable
              style="width: 100%;"
              @change="onSchemaChange"
            >
              <el-option
                v-for="schema in schemas"
                :key="schema"
                :label="schema"
                :value="schema"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="selection-group">
            <label class="selection-label">
              Tables
              <el-button text size="small" @click="selectAllTables">Select All</el-button>
              <el-button text size="small" @click="selectedTables = []">Clear</el-button>
            </label>
            <el-select
              v-model="selectedTables"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="Select tables"
              style="width: 100%;"
            >
              <el-option
                v-for="table in tables"
                :key="table"
                :label="table"
                :value="table"
              />
            </el-select>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Generator Tabs -->
    <el-tabs v-model="activeGenTab" type="border-card" class="generator-tabs" v-if="selectedTables.length > 0">
      <!-- Document Tab -->
      <el-tab-pane label="Document" name="doc">
        <div class="gen-options">
          <el-row :gutter="20" align="middle">
            <el-col :span="6">
              <label class="option-label">Format</label>
              <el-select v-model="docFormat" style="width: 100%;">
                <el-option label="Markdown" value="markdown" />
                <el-option label="Word (.docx)" value="word" />
                <el-option label="PDF" value="pdf" />
              </el-select>
            </el-col>
            <el-col :span="6">
              <label class="option-label">Include</label>
              <el-checkbox-group v-model="docIncludes">
                <el-checkbox label="columns" value="columns">Columns</el-checkbox>
                <el-checkbox label="indexes" value="indexes">Indexes</el-checkbox>
                <el-checkbox label="foreign_keys" value="foreign_keys">Foreign Keys</el-checkbox>
              </el-checkbox-group>
            </el-col>
            <el-col :span="12" class="gen-actions">
              <el-button type="primary" @click="handleGenerateDoc" :loading="generating">
                <el-icon><Document /></el-icon>
                Generate
              </el-button>
              <el-button @click="handleDownloadDoc" :disabled="!docResult" plain>
                <el-icon><Download /></el-icon>
                Download
              </el-button>
            </el-col>
          </el-row>
        </div>
        <div class="gen-preview" v-if="docResult">
          <pre class="preview-content">{{ docResult }}</pre>
        </div>
        <el-empty v-else description="Configure options and click Generate" :image-size="80" />
      </el-tab-pane>

      <!-- Code Tab -->
      <el-tab-pane label="Code" name="code">
        <div class="gen-options">
          <el-row :gutter="20" align="middle">
            <el-col :span="5">
              <label class="option-label">Language</label>
              <el-select v-model="codeLanguage" style="width: 100%;">
                <el-option label="Java" value="java" />
                <el-option label="Python" value="python" />
                <el-option label="Go" value="go" />
                <el-option label="TypeScript" value="typescript" />
                <el-option label="C#" value="csharp" />
                <el-option label="Rust" value="rust" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <label class="option-label">Naming Style</label>
              <el-select v-model="codeNamingStyle" style="width: 100%;">
                <el-option label="Camel Case" value="camel" />
                <el-option label="Snake Case" value="snake" />
                <el-option label="Pascal Case" value="pascal" />
              </el-select>
            </el-col>
            <el-col :span="4">
              <label class="option-label">Options</label>
              <el-checkbox v-model="codeIncludeComments">Comments</el-checkbox>
            </el-col>
            <el-col :span="10" class="gen-actions">
              <el-button type="primary" @click="handleGenerateCode" :loading="generating">
                <el-icon><EditPen /></el-icon>
                Generate
              </el-button>
              <el-button @click="handleCopyCode" :disabled="!codeResult" plain>
                <el-icon><CopyDocument /></el-icon>
                Copy
              </el-button>
              <el-button @click="handleDownloadCode" :disabled="!codeResult" plain>
                <el-icon><Download /></el-icon>
                Download
              </el-button>
            </el-col>
          </el-row>
        </div>
        <div class="gen-preview code-preview" v-if="codeResult">
          <pre class="preview-content"><code>{{ codeResult }}</code></pre>
        </div>
        <el-empty v-else description="Configure options and click Generate" :image-size="80" />
      </el-tab-pane>

      <!-- DDL Tab -->
      <el-tab-pane label="DDL" name="ddl">
        <div class="gen-options">
          <el-row :gutter="20" align="middle">
            <el-col :span="4">
              <el-checkbox v-model="ddlIncludeIndexes">Indexes</el-checkbox>
            </el-col>
            <el-col :span="4">
              <el-checkbox v-model="ddlIncludeFKs">Foreign Keys</el-checkbox>
            </el-col>
            <el-col :span="5">
              <label class="option-label">Target Dialect</label>
              <el-select v-model="ddlTargetDialect" style="width: 100%;" clearable>
                <el-option label="Same as source" value="" />
                <el-option label="MySQL" value="mysql" />
                <el-option label="PostgreSQL" value="postgresql" />
                <el-option label="Oracle" value="oracle" />
              </el-select>
            </el-col>
            <el-col :span="11" class="gen-actions">
              <el-button type="primary" @click="handleGenerateDDL" :loading="generating">
                <el-icon><Document /></el-icon>
                Generate DDL
              </el-button>
              <el-button @click="handleCopyDDL" :disabled="!ddlResult" plain>
                <el-icon><CopyDocument /></el-icon>
                Copy
              </el-button>
              <el-button @click="handleDownloadDDL" :disabled="!ddlResult" plain>
                <el-icon><Download /></el-icon>
                Download
              </el-button>
            </el-col>
          </el-row>
        </div>
        <div class="gen-preview code-preview" v-if="ddlResult">
          <pre class="preview-content"><code>{{ ddlResult }}</code></pre>
        </div>
        <el-empty v-else description="Configure options and click Generate" :image-size="80" />
      </el-tab-pane>
    </el-tabs>

    <div class="empty-generator" v-else>
      <el-empty description="Select a connection and tables to generate output" :image-size="120" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import { getSchemas, getTables, generateDoc, generateCode, generateDDL, convertDDL } from '@/api/index.js'

const connectionStore = useConnectionStore()

const selectedConnectionId = ref(null)
const selectedSchema = ref('')
const schemas = ref([])
const tables = ref([])
const selectedTables = ref([])
const activeGenTab = ref('doc')
const generating = ref(false)

// Document options
const docFormat = ref('markdown')
const docIncludes = ref(['columns', 'indexes', 'foreign_keys'])
const docResult = ref('')

// Code options
const codeLanguage = ref('java')
const codeNamingStyle = ref('camel')
const codeIncludeComments = ref(true)
const codeResult = ref('')

// DDL options
const ddlIncludeIndexes = ref(true)
const ddlIncludeFKs = ref(true)
const ddlTargetDialect = ref('')
const ddlResult = ref('')

onMounted(() => {
  connectionStore.fetchConnections().then(() => {
    if (connectionStore.currentConnection) {
      selectedConnectionId.value = connectionStore.currentConnection.id
      onConnectionChange(selectedConnectionId.value)
    }
  })
})

async function onConnectionChange(connId) {
  selectedSchema.value = ''
  schemas.value = []
  tables.value = []
  selectedTables.value = []

  if (!connId) return

  try {
    const response = await getSchemas(connId)
    const data = response.data || response || []
    schemas.value = data.map(s => s.name || s)
    if (schemas.value.length > 0) {
      selectedSchema.value = schemas.value[0]
      onSchemaChange(selectedSchema.value)
    }
  } catch (error) {
    schemas.value = []
  }
}

async function onSchemaChange(schema) {
  tables.value = []
  selectedTables.value = []

  if (!schema || !selectedConnectionId.value) return

  try {
    const response = await getTables(selectedConnectionId.value, schema)
    const data = response.data || response || []
    tables.value = data.map(t => t.name || t.table_name || t)
  } catch (error) {
    tables.value = []
  }
}

function selectAllTables() {
  selectedTables.value = [...tables.value]
}

async function handleGenerateDoc() {
  if (!validateSelection()) return

  generating.value = true
  docResult.value = ''
  try {
    const response = await generateDoc({
      connection_id: selectedConnectionId.value,
      schema: selectedSchema.value,
      tables: selectedTables.value,
      format: docFormat.value,
      includes: docIncludes.value
    })

    // If the response is a blob (for word/pdf), handle differently
    if (response instanceof Blob) {
      docResult.value = `[Binary document generated - click Download to save]`
      // Store blob for download
      docResult._blob = response
    } else {
      const data = response.data || response
      docResult.value = typeof data === 'string' ? data : (data.content || JSON.stringify(data, null, 2))
    }
    ElMessage.success('Document generated')
  } catch (error) {
    ElMessage.error('Failed to generate document')
  } finally {
    generating.value = false
  }
}

async function handleGenerateCode() {
  if (!validateSelection()) return

  generating.value = true
  codeResult.value = ''
  try {
    const response = await generateCode({
      connection_id: selectedConnectionId.value,
      schema: selectedSchema.value,
      tables: selectedTables.value,
      language: codeLanguage.value,
      naming_style: codeNamingStyle.value,
      include_comments: codeIncludeComments.value
    })
    const data = response.data || response
    codeResult.value = typeof data === 'string' ? data : (data.code || data.content || JSON.stringify(data, null, 2))
    ElMessage.success('Code generated')
  } catch (error) {
    ElMessage.error('Failed to generate code')
  } finally {
    generating.value = false
  }
}

async function handleGenerateDDL() {
  if (!validateSelection()) return

  generating.value = true
  ddlResult.value = ''
  try {
    let response
    if (ddlTargetDialect.value) {
      // First generate, then convert
      const genResponse = await generateDDL({
        connection_id: selectedConnectionId.value,
        schema: selectedSchema.value,
        tables: selectedTables.value,
        include_indexes: ddlIncludeIndexes.value,
        include_foreign_keys: ddlIncludeFKs.value
      })
      const genData = genResponse.data || genResponse
      const ddl = typeof genData === 'string' ? genData : (genData.ddl || genData.content || '')

      response = await convertDDL({
        ddl: ddl,
        target_dialect: ddlTargetDialect.value
      })
    } else {
      response = await generateDDL({
        connection_id: selectedConnectionId.value,
        schema: selectedSchema.value,
        tables: selectedTables.value,
        include_indexes: ddlIncludeIndexes.value,
        include_foreign_keys: ddlIncludeFKs.value
      })
    }
    const data = response.data || response
    ddlResult.value = typeof data === 'string' ? data : (data.ddl || data.content || JSON.stringify(data, null, 2))
    ElMessage.success('DDL generated')
  } catch (error) {
    ElMessage.error('Failed to generate DDL')
  } finally {
    generating.value = false
  }
}

function validateSelection() {
  if (!selectedConnectionId.value) {
    ElMessage.warning('Please select a connection')
    return false
  }
  if (selectedTables.value.length === 0) {
    ElMessage.warning('Please select at least one table')
    return false
  }
  return true
}

function handleCopyCode() {
  copyToClipboard(codeResult.value)
}

function handleCopyDDL() {
  copyToClipboard(ddlResult.value)
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('Copied to clipboard')
  }).catch(() => {
    // Fallback
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('Copied to clipboard')
  })
}

function handleDownloadDoc() {
  if (docResult.value._blob) {
    downloadBlob(docResult.value._blob, `document.${getFileExtension(docFormat.value)}`)
  } else {
    downloadText(docResult.value, `document.${getFileExtension(docFormat.value)}`)
  }
}

function handleDownloadCode() {
  const ext = getCodeExtension(codeLanguage.value)
  downloadText(codeResult.value, `generated.${ext}`)
}

function handleDownloadDDL() {
  downloadText(ddlResult.value, 'schema.sql')
}

function downloadText(content, filename) {
  const blob = new Blob([content], { type: 'text/plain' })
  downloadBlob(blob, filename)
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function getFileExtension(format) {
  switch (format) {
    case 'markdown': return 'md'
    case 'word': return 'docx'
    case 'pdf': return 'pdf'
    default: return 'txt'
  }
}

function getCodeExtension(language) {
  switch (language) {
    case 'java': return 'java'
    case 'python': return 'py'
    case 'go': return 'go'
    case 'typescript': return 'ts'
    case 'csharp': return 'cs'
    case 'rust': return 'rs'
    default: return 'txt'
  }
}
</script>

<style scoped>
.generator-page {
  height: calc(100vh - 98px);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.selection-panel {
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.selection-group {
  margin-bottom: 4px;
}

.selection-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 6px;
}

.generator-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
}

.generator-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.gen-options {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.option-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 6px;
}

.gen-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.gen-preview {
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
  max-height: calc(100vh - 380px);
}

.code-preview {
  background: #1e1e1e;
}

.code-preview .preview-content {
  color: #d4d4d4;
}

.preview-content {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-generator {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 8px;
}
</style>
