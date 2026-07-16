<template>
  <div class="api-gateway-page">
    <div class="page-header">
      <h2 class="page-title">API Gateway</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        Create API
      </el-button>
    </div>

    <div class="gateway-content">
      <!-- Left: API List -->
      <div class="api-list-panel">
        <div class="list-search">
          <el-input
            v-model="searchQuery"
            placeholder="Search APIs..."
            clearable
            size="default"
            prefix-icon="Search"
          />
        </div>
        <div class="api-list" v-loading="listLoading">
          <div
            v-for="api in filteredApis"
            :key="api.id"
            class="api-list-item"
            :class="{ 'is-active': selectedApi?.id === api.id }"
            @click="selectApi(api)"
          >
            <div class="api-item-header">
              <el-tag
                :type="getMethodType(api.method)"
                size="small"
                class="method-tag"
              >
                {{ api.method }}
              </el-tag>
              <el-switch
                :model-value="api.enabled"
                size="small"
                @change="handleToggleApi(api)"
                @click.stop
              />
            </div>
            <div class="api-item-name">{{ api.name }}</div>
            <div class="api-item-path">{{ api.url_path || api.path }}</div>
          </div>
          <el-empty
            v-if="!listLoading && filteredApis.length === 0"
            :description="searchQuery ? 'No matching APIs' : 'No APIs created yet'"
            :image-size="80"
          />
        </div>
      </div>

      <!-- Right: API Detail -->
      <div class="api-detail-panel">
        <template v-if="selectedApi">
          <div class="detail-toolbar">
            <h3 class="detail-title">{{ selectedApi.name }}</h3>
            <div class="detail-actions">
              <el-button size="small" @click="handleEditApi" plain>
                <el-icon><Edit /></el-icon>
                Edit
              </el-button>
              <el-popconfirm
                title="Delete this API?"
                confirm-button-text="Delete"
                @confirm="handleDeleteApi"
              >
                <template #reference>
                  <el-button size="small" type="danger" plain>
                    <el-icon><Delete /></el-icon>
                    Delete
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <el-tabs v-model="detailTab" type="border-card" class="detail-tabs">
            <!-- Config Tab -->
            <el-tab-pane label="Configuration" name="config">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="Name">{{ selectedApi.name }}</el-descriptions-item>
                <el-descriptions-item label="Method">
                  <el-tag :type="getMethodType(selectedApi.method)" size="small">
                    {{ selectedApi.method }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="URL Path" :span="2">
                  <code>{{ selectedApi.url_path || selectedApi.path }}</code>
                </el-descriptions-item>
                <el-descriptions-item label="Connection">
                  {{ getConnectionName(selectedApi.connection_id) }}
                </el-descriptions-item>
                <el-descriptions-item label="Status">
                  <el-tag :type="selectedApi.enabled ? 'success' : 'danger'" size="small">
                    {{ selectedApi.enabled ? 'Enabled' : 'Disabled' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="Auth Type">
                  {{ selectedApi.auth_type || 'None' }}
                </el-descriptions-item>
                <el-descriptions-item label="Rate Limit">
                  {{ selectedApi.rate_limit ? `${selectedApi.rate_limit} req/min` : 'Unlimited' }}
                </el-descriptions-item>
              </el-descriptions>

              <div class="sql-section">
                <h4 class="section-subtitle">SQL Template</h4>
                <pre class="sql-preview"><code>{{ selectedApi.sql_template || selectedApi.sql || '' }}</code></pre>
              </div>

              <div class="params-section" v-if="selectedApi.params && selectedApi.params.length > 0">
                <h4 class="section-subtitle">Parameters</h4>
                <el-table :data="selectedApi.params" stripe border size="small">
                  <el-table-column prop="name" label="Name" min-width="120" />
                  <el-table-column prop="type" label="Type" width="100" />
                  <el-table-column prop="required" label="Required" width="80" align="center">
                    <template #default="{ row }">
                      <el-tag :type="row.required ? 'danger' : 'info'" size="small">
                        {{ row.required ? 'Yes' : 'No' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="default" label="Default" min-width="100">
                    <template #default="{ row }">
                      {{ row.default ?? '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="description" label="Description" min-width="160">
                    <template #default="{ row }">
                      {{ row.description || '' }}
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- Test Tab -->
            <el-tab-pane label="Test" name="test">
              <div class="test-panel">
                <h4 class="section-subtitle">Request Parameters</h4>
                <div class="test-params">
                  <div
                    v-for="(param, index) in testParams"
                    :key="index"
                    class="test-param-row"
                  >
                    <el-input v-model="param.key" placeholder="Parameter name" size="small" style="width: 200px;" />
                    <span class="param-separator">=</span>
                    <el-input v-model="param.value" placeholder="Value" size="small" style="flex: 1;" />
                    <el-button text type="danger" size="small" @click="removeTestParam(index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" text @click="addTestParam">
                    <el-icon><Plus /></el-icon>
                    Add Parameter
                  </el-button>
                </div>

                <div class="test-actions">
                  <el-button type="primary" @click="handleCallApi" :loading="testLoading">
                    <el-icon><Promotion /></el-icon>
                    Send Request
                  </el-button>
                  <el-button @click="handleExtractParams" plain size="small">
                    <el-icon><MagicStick /></el-icon>
                    Extract Params from SQL
                  </el-button>
                </div>

                <div class="test-response" v-if="testResponse">
                  <h4 class="section-subtitle">
                    Response
                    <el-tag size="small" :type="testResponse.status === 'success' ? 'success' : 'danger'" v-if="testResponse.status">
                      {{ testResponse.status }}
                    </el-tag>
                    <el-tag size="small" type="info" v-if="testResponse.duration_ms">
                      {{ testResponse.duration_ms }}ms
                    </el-tag>
                  </h4>
                  <pre class="response-content"><code>{{ JSON.stringify(testResponse.data || testResponse, null, 2) }}</code></pre>
                </div>
              </div>
            </el-tab-pane>

            <!-- Monitoring Tab -->
            <el-tab-pane label="Monitoring" name="monitoring">
              <div class="monitoring-panel">
                <!-- Statistics Section -->
                <h4 class="section-subtitle">Statistics</h4>
                <div class="stats-cards" v-loading="statsLoading">
                  <el-row :gutter="16">
                    <el-col :span="6">
                      <el-card shadow="never" class="stat-card">
                        <el-statistic title="Total Calls" :value="apiStats.total_calls ?? 0" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card shadow="never" class="stat-card">
                        <el-statistic title="Success Rate" :value="apiStats.success_rate ?? 0" suffix="%" :precision="1" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card shadow="never" class="stat-card">
                        <el-statistic title="Avg Response Time" :value="apiStats.avg_response_time ?? 0" suffix="ms" :precision="1" />
                      </el-card>
                    </el-col>
                    <el-col :span="6">
                      <el-card shadow="never" class="stat-card">
                        <el-statistic title="Calls Today" :value="apiStats.calls_today ?? 0" />
                      </el-card>
                    </el-col>
                  </el-row>
                </div>

                <!-- Call Logs Section -->
                <div class="logs-header">
                  <h4 class="section-subtitle" style="margin-bottom: 0;">Call Logs</h4>
                  <el-button size="small" @click="fetchMonitoringData" :loading="logsLoading" plain>
                    <el-icon><Refresh /></el-icon>
                    Refresh
                  </el-button>
                </div>
                <el-table
                  :data="apiLogs"
                  stripe
                  border
                  size="small"
                  v-loading="logsLoading"
                  style="width: 100%; margin-top: 10px;"
                  max-height="360"
                  empty-text="No call logs yet"
                >
                  <el-table-column prop="timestamp" label="Timestamp" min-width="170">
                    <template #default="{ row }">
                      {{ row.timestamp || row.created_at || '-' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="method" label="Method" width="90" align="center">
                    <template #default="{ row }">
                      <el-tag :type="getMethodType(row.method)" size="small">
                        {{ row.method || '-' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status_code" label="Status" width="90" align="center">
                    <template #default="{ row }">
                      <el-tag
                        :type="(row.status_code >= 200 && row.status_code < 300) ? 'success' : (row.status_code >= 400 ? 'danger' : 'warning')"
                        size="small"
                      >
                        {{ row.status_code || '-' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="response_time" label="Response Time" width="120" align="right">
                    <template #default="{ row }">
                      {{ row.response_time != null ? `${row.response_time}ms` : (row.duration_ms != null ? `${row.duration_ms}ms` : '-') }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="client_ip" label="Client IP" min-width="130">
                    <template #default="{ row }">
                      {{ row.client_ip || row.remote_addr || '-' }}
                    </template>
                  </el-table-column>
                </el-table>

                <!-- Regenerate Token Section -->
                <div class="token-section">
                  <el-divider />
                  <div class="token-actions">
                    <span class="token-label">API Token Management</span>
                    <el-popconfirm
                      title="Regenerating the token will invalidate the current token. Continue?"
                      confirm-button-text="Regenerate"
                      cancel-button-text="Cancel"
                      @confirm="handleRegenerateToken"
                      width="320"
                    >
                      <template #reference>
                        <el-button type="warning" plain size="small" :loading="regenerating">
                          <el-icon><RefreshRight /></el-icon>
                          Regenerate Token
                        </el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <div class="empty-detail" v-else>
          <el-empty description="Select an API to view details" :image-size="120">
            <template #image>
              <el-icon :size="64" color="#c0c4cc"><Share /></el-icon>
            </template>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- Create/Edit API Dialog -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEditing ? 'Edit API' : 'Create API'"
      width="720px"
      destroy-on-close
    >
      <el-form ref="apiFormRef" :model="apiForm" :rules="apiFormRules" label-width="120px">
        <el-form-item label="Name" prop="name">
          <el-input v-model="apiForm.name" placeholder="API name" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Method" prop="method">
              <el-select v-model="apiForm.method" style="width: 100%;">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="URL Path" prop="url_path">
              <el-input v-model="apiForm.url_path" placeholder="/api/v1/users/:id" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Connection" prop="connection_id">
          <el-select v-model="apiForm.connection_id" placeholder="Select connection" filterable style="width: 100%;">
            <el-option
              v-for="conn in connectionStore.connections"
              :key="conn.id"
              :label="`${conn.name} (${conn.db_type})`"
              :value="conn.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="SQL Template" prop="sql_template">
          <el-input
            v-model="apiForm.sql_template"
            type="textarea"
            :rows="6"
            placeholder="SELECT * FROM users WHERE id = :id"
          />
        </el-form-item>

        <el-form-item label="Parameters">
          <div class="form-params">
            <div v-for="(param, index) in apiForm.params" :key="index" class="form-param-row">
              <el-input v-model="param.name" placeholder="Name" size="small" style="width: 140px;" />
              <el-select v-model="param.type" placeholder="Type" size="small" style="width: 100px;">
                <el-option label="String" value="string" />
                <el-option label="Integer" value="integer" />
                <el-option label="Float" value="float" />
                <el-option label="Boolean" value="boolean" />
              </el-select>
              <el-checkbox v-model="param.required" size="small">Required</el-checkbox>
              <el-input v-model="param.default" placeholder="Default" size="small" style="width: 100px;" />
              <el-button text type="danger" size="small" @click="apiForm.params.splice(index, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-button size="small" text @click="apiForm.params.push({ name: '', type: 'string', required: false, default: '' })">
              <el-icon><Plus /></el-icon> Add Parameter
            </el-button>
          </div>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Auth Type">
              <el-select v-model="apiForm.auth_type" style="width: 100%;">
                <el-option label="None" value="none" />
                <el-option label="Token" value="token" />
                <el-option label="API Key" value="api_key" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Rate Limit">
              <el-input-number v-model="apiForm.rate_limit" :min="0" :max="10000" placeholder="req/min" controls-position="right" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="formDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveApi" :loading="savingApi">
          {{ isEditing ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import {
  getApis,
  createApi,
  updateApi,
  deleteApi,
  toggleApi,
  extractParams,
  callApi,
  getApiLogs,
  getApiStats,
  regenerateToken
} from '@/api/index.js'

const connectionStore = useConnectionStore()

const searchQuery = ref('')
const apiList = ref([])
const listLoading = ref(false)
const selectedApi = ref(null)
const detailTab = ref('config')

// Form state
const formDialogVisible = ref(false)
const isEditing = ref(false)
const editingApiId = ref(null)
const savingApi = ref(false)
const apiFormRef = ref(null)

const apiForm = reactive({
  name: '',
  method: 'GET',
  url_path: '',
  connection_id: null,
  sql_template: '',
  params: [],
  auth_type: 'none',
  rate_limit: 60
})

const apiFormRules = {
  name: [{ required: true, message: 'Please enter API name', trigger: 'blur' }],
  method: [{ required: true, message: 'Please select method', trigger: 'change' }],
  url_path: [{ required: true, message: 'Please enter URL path', trigger: 'blur' }],
  connection_id: [{ required: true, message: 'Please select connection', trigger: 'change' }],
  sql_template: [{ required: true, message: 'Please enter SQL template', trigger: 'blur' }]
}

// Test state
const testParams = ref([{ key: '', value: '' }])
const testLoading = ref(false)
const testResponse = ref(null)

// Monitoring state
const apiLogs = ref([])
const apiStats = reactive({
  total_calls: 0,
  success_rate: 0,
  avg_response_time: 0,
  calls_today: 0
})
const logsLoading = ref(false)
const statsLoading = ref(false)
const regenerating = ref(false)

watch(detailTab, (newTab) => {
  if (newTab === 'monitoring' && selectedApi.value) {
    fetchMonitoringData()
  }
})

const filteredApis = computed(() => {
  if (!searchQuery.value) return apiList.value
  const q = searchQuery.value.toLowerCase()
  return apiList.value.filter(api =>
    api.name.toLowerCase().includes(q) ||
    (api.url_path || api.path || '').toLowerCase().includes(q)
  )
})

onMounted(() => {
  connectionStore.fetchConnections()
  fetchApiList()
})

async function fetchApiList() {
  listLoading.value = true
  try {
    const response = await getApis()
    apiList.value = response.data || response || []
  } catch (error) {
    apiList.value = []
  } finally {
    listLoading.value = false
  }
}

function selectApi(api) {
  selectedApi.value = api
  detailTab.value = 'config'
  testResponse.value = null
  // Initialize test params from API params
  if (api.params && api.params.length > 0) {
    testParams.value = api.params.map(p => ({ key: p.name, value: p.default || '' }))
  } else {
    testParams.value = [{ key: '', value: '' }]
  }
}

function openCreateDialog() {
  isEditing.value = false
  editingApiId.value = null
  Object.assign(apiForm, {
    name: '',
    method: 'GET',
    url_path: '',
    connection_id: connectionStore.currentConnection?.id || null,
    sql_template: '',
    params: [],
    auth_type: 'none',
    rate_limit: 60
  })
  formDialogVisible.value = true
}

function handleEditApi() {
  if (!selectedApi.value) return
  isEditing.value = true
  editingApiId.value = selectedApi.value.id
  Object.assign(apiForm, {
    name: selectedApi.value.name,
    method: selectedApi.value.method,
    url_path: selectedApi.value.url_path || selectedApi.value.path || '',
    connection_id: selectedApi.value.connection_id,
    sql_template: selectedApi.value.sql_template || selectedApi.value.sql || '',
    params: selectedApi.value.params ? selectedApi.value.params.map(p => ({ ...p })) : [],
    auth_type: selectedApi.value.auth_type || 'none',
    rate_limit: selectedApi.value.rate_limit || 60
  })
  formDialogVisible.value = true
}

async function handleSaveApi() {
  try {
    await apiFormRef.value.validate()
  } catch {
    return
  }

  savingApi.value = true
  try {
    const payload = { ...apiForm }
    if (isEditing.value) {
      await updateApi(editingApiId.value, payload)
      ElMessage.success('API updated')
    } else {
      await createApi(payload)
      ElMessage.success('API created')
    }
    formDialogVisible.value = false
    await fetchApiList()
    // Re-select if editing
    if (isEditing.value) {
      const updated = apiList.value.find(a => a.id === editingApiId.value)
      if (updated) selectApi(updated)
    }
  } catch (error) {
    ElMessage.error('Failed to save API')
  } finally {
    savingApi.value = false
  }
}

async function handleDeleteApi() {
  if (!selectedApi.value) return
  try {
    await deleteApi(selectedApi.value.id)
    ElMessage.success('API deleted')
    selectedApi.value = null
    await fetchApiList()
  } catch (error) {
    ElMessage.error('Failed to delete API')
  }
}

async function handleToggleApi(api) {
  try {
    await toggleApi(api.id)
    api.enabled = !api.enabled
    ElMessage.success(`API ${api.enabled ? 'enabled' : 'disabled'}`)
  } catch (error) {
    ElMessage.error('Failed to toggle API')
  }
}

function addTestParam() {
  testParams.value.push({ key: '', value: '' })
}

function removeTestParam(index) {
  testParams.value.splice(index, 1)
}

async function handleCallApi() {
  if (!selectedApi.value) return

  testLoading.value = true
  testResponse.value = null
  try {
    const params = {}
    for (const p of testParams.value) {
      if (p.key) {
        params[p.key] = p.value
      }
    }
    const response = await callApi(selectedApi.value.id, params)
    testResponse.value = response.data || response
  } catch (error) {
    testResponse.value = {
      status: 'error',
      message: error.response?.data?.detail || error.message || 'Request failed',
      data: error.response?.data || null
    }
  } finally {
    testLoading.value = false
  }
}

async function handleExtractParams() {
  const sql = apiForm.sql_template || selectedApi.value?.sql_template || selectedApi.value?.sql
  if (!sql) {
    ElMessage.warning('No SQL template to extract params from')
    return
  }
  try {
    const response = await extractParams(sql)
    const data = response.data || response
    const params = data.params || data || []
    if (Array.isArray(params) && params.length > 0) {
      testParams.value = params.map(p => {
        if (typeof p === 'string') {
          return { key: p, value: '' }
        }
        return { key: p.name || p, value: p.default || '' }
      })
      ElMessage.success(`Extracted ${params.length} parameters`)
    } else {
      ElMessage.info('No parameters found in SQL')
    }
  } catch (error) {
    ElMessage.error('Failed to extract parameters')
  }
}

async function fetchMonitoringData() {
  if (!selectedApi.value) return
  await Promise.all([fetchApiLogs(), fetchApiStats()])
}

async function fetchApiLogs() {
  if (!selectedApi.value) return
  logsLoading.value = true
  try {
    const response = await getApiLogs(selectedApi.value.id)
    const data = response.data || response || []
    apiLogs.value = Array.isArray(data) ? data : (data.logs || data.items || [])
  } catch (error) {
    apiLogs.value = []
  } finally {
    logsLoading.value = false
  }
}

async function fetchApiStats() {
  if (!selectedApi.value) return
  statsLoading.value = true
  try {
    const response = await getApiStats(selectedApi.value.id)
    const data = response.data || response || {}
    Object.assign(apiStats, {
      total_calls: data.total_calls ?? 0,
      success_rate: data.success_rate ?? 0,
      avg_response_time: data.avg_response_time ?? 0,
      calls_today: data.calls_today ?? 0
    })
  } catch (error) {
    Object.assign(apiStats, {
      total_calls: 0,
      success_rate: 0,
      avg_response_time: 0,
      calls_today: 0
    })
  } finally {
    statsLoading.value = false
  }
}

async function handleRegenerateToken() {
  if (!selectedApi.value) return
  regenerating.value = true
  try {
    const response = await regenerateToken(selectedApi.value.id)
    const data = response.data || response || {}
    if (data.token) {
      ElMessage.success('Token regenerated successfully')
    } else {
      ElMessage.success(data.message || 'Token regenerated')
    }
  } catch (error) {
    ElMessage.error('Failed to regenerate token')
  } finally {
    regenerating.value = false
  }
}

function getMethodType(method) {
  switch (method?.toUpperCase()) {
    case 'GET': return 'success'
    case 'POST': return 'primary'
    case 'PUT': return 'warning'
    case 'DELETE': return 'danger'
    default: return 'info'
  }
}

function getConnectionName(connId) {
  const conn = connectionStore.connections.find(c => c.id === connId)
  return conn ? conn.name : String(connId)
}
</script>

<style scoped>
.api-gateway-page {
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

.gateway-content {
  flex: 1;
  display: flex;
  gap: 0;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.api-list-panel {
  width: 300px;
  min-width: 260px;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.list-search {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
}

.api-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.api-list-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.api-list-item:hover {
  background: #f5f7fa;
  border-color: #c6e2ff;
}

.api-list-item.is-active {
  background: #ecf5ff;
  border-color: #409eff;
}

.api-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.method-tag {
  font-weight: 700;
  letter-spacing: 0.5px;
  font-size: 11px;
}

.api-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.api-item-path {
  font-size: 12px;
  color: #909399;
  font-family: 'Consolas', 'Monaco', monospace;
}

.api-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-tabs {
  flex: 1;
  overflow: auto;
  border: none;
}

.detail-tabs :deep(.el-tabs__content) {
  padding: 16px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin: 16px 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-subtitle:first-child {
  margin-top: 0;
}

.sql-section {
  margin-top: 16px;
}

.sql-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  margin: 0;
}

.params-section {
  margin-top: 16px;
}

/* Test Panel */
.test-panel {
  padding: 0;
}

.test-params {
  margin-bottom: 16px;
}

.test-param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.param-separator {
  color: #909399;
  font-size: 14px;
  font-weight: 600;
}

.test-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.test-response {
  margin-top: 16px;
}

.response-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}

/* Form params */
.form-params {
  width: 100%;
}

.form-param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.empty-detail {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Monitoring Panel */
.monitoring-panel {
  padding: 0;
}

.stats-cards {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.stat-card :deep(.el-statistic__head) {
  font-size: 12px;
  color: #909399;
}

.stat-card :deep(.el-statistic__content) {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.token-section {
  margin-top: 8px;
}

.token-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.token-label {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
</style>
