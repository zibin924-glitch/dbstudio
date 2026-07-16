import axios from 'axios'
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// H-F4: 全局后端可达状态（响应式，供组件使用）
export const backendStatus = reactive({
  reachable: true,
  lastError: null
})

// H-F4: 错误提示防抖 —— 3 秒内最多弹出一个错误 toast
let lastErrorToastTime = 0
function showDebouncedError(message) {
  const now = Date.now()
  if (now - lastErrorToastTime < 3000) return
  lastErrorToastTime = now
  ElMessage.error(message)
}

// Request interceptor
apiClient.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  response => {
    // H-F4: 请求成功，标记后端可达
    backendStatus.reachable = true
    backendStatus.lastError = null
    return response.data
  },
  error => {
    // H-F4: 区分网络不可达和服务器错误
    if (!error.response) {
      // 没有响应 —— 网络错误或后端不可达
      backendStatus.reachable = false
      backendStatus.lastError = error.message || '网络连接失败'
      showDebouncedError('后端服务不可达，请检查服务是否正常运行')
    } else {
      // 有响应但是错误状态码 —— 后端可达但返回了错误
      backendStatus.reachable = true
      backendStatus.lastError = null
      const message = error.response?.data?.detail || error.message || 'Request failed'
      showDebouncedError(message)
    }
    return Promise.reject(error)
  }
)

// ==========================================
// Connection APIs
// ==========================================
export function getConnections() {
  return apiClient.get('/connections')
}

export function getConnection(id) {
  return apiClient.get(`/connections/${id}`)
}

export function createConnection(data) {
  return apiClient.post('/connections', data)
}

export function updateConnection(id, data) {
  return apiClient.put(`/connections/${id}`, data)
}

export function deleteConnection(id) {
  return apiClient.delete(`/connections/${id}`)
}

export function testConnection(data) {
  return apiClient.post('/connections/test', data)
}

// ==========================================
// Explorer APIs
// ==========================================
export function getSchemas(connectionId) {
  return apiClient.get('/explorer/schemas', {
    params: { connection_id: connectionId }
  })
}

export function getTables(connectionId, schema) {
  return apiClient.get('/explorer/tables', {
    params: { connection_id: connectionId, schema }
  })
}

export function getColumns(connectionId, schema, tableName) {
  return apiClient.get('/explorer/columns', {
    params: { connection_id: connectionId, schema, table_name: tableName }
  })
}

export function getIndexes(connectionId, schema, tableName) {
  return apiClient.get('/explorer/indexes', {
    params: { connection_id: connectionId, schema, table_name: tableName }
  })
}

export function getForeignKeys(connectionId, schema, tableName) {
  return apiClient.get('/explorer/foreign-keys', {
    params: { connection_id: connectionId, schema, table_name: tableName }
  })
}

export function getTableData(connectionId, schema, tableName, page = 1, pageSize = 100) {
  return apiClient.get('/explorer/data', {
    params: { connection_id: connectionId, schema, table_name: tableName, page, page_size: pageSize }
  })
}

export function getStats(connectionId) {
  return apiClient.get('/explorer/stats', {
    params: { connection_id: connectionId }
  })
}

export function getProcedures(connectionId, schema) {
  return apiClient.get(`/explorer/${connectionId}/procedures`, {
    params: { schema }
  })
}

export function getTriggers(connectionId, schema) {
  return apiClient.get(`/explorer/${connectionId}/triggers`, {
    params: { schema }
  })
}

export function getFunctions(connectionId, schema) {
  return apiClient.get(`/explorer/${connectionId}/functions`, {
    params: { schema }
  })
}

export function getSequences(connectionId, schema) {
  return apiClient.get(`/explorer/${connectionId}/sequences`, {
    params: { schema }
  })
}

// ==========================================
// Query APIs
// ==========================================
export function executeQuery(data) {
  return apiClient.post('/query/execute', data)
}

export function exportResults(data) {
  return apiClient.post('/query/export', data, { responseType: 'blob' })
}

export function getHistory(params) {
  return apiClient.get('/query/history', { params })
}

export function toggleFavorite(historyId) {
  return apiClient.post(`/query/history/${historyId}/toggle-favorite`)
}

// ==========================================
// Generator APIs
// ==========================================
export function generateDoc(data) {
  return apiClient.post('/generator/doc', data, { responseType: 'blob' })
}

export function generateCode(data) {
  return apiClient.post('/generator/code', data)
}

export function generateDDL(data) {
  return apiClient.post('/generator/ddl', data)
}

export function convertDDL(data) {
  return apiClient.post('/generator/ddl/convert', data)
}

// ==========================================
// API Gateway APIs
// ==========================================
export function getApis(params) {
  return apiClient.get('/gateway/apis', { params })
}

export function getApi(id) {
  return apiClient.get(`/gateway/apis/${id}`)
}

export function createApi(data) {
  return apiClient.post('/gateway/apis', data)
}

export function updateApi(id, data) {
  return apiClient.put(`/gateway/apis/${id}`, data)
}

export function deleteApi(id) {
  return apiClient.delete(`/gateway/apis/${id}`)
}

export function toggleApi(id) {
  return apiClient.post(`/gateway/apis/${id}/toggle`)
}

export function extractParams(sql) {
  return apiClient.post('/gateway/apis/extract-params', { sql })
}

export function callApi(apiId, params) {
  return apiClient.post(`/gateway/apis/${apiId}/call`, params)
}

export function getApiLogs(apiId, params) {
  return apiClient.get(`/gateway/apis/${apiId}/logs`, { params })
}

export function getApiStats(apiId) {
  return apiClient.get(`/gateway/apis/${apiId}/stats`)
}

export function regenerateToken(apiId) {
  return apiClient.post(`/gateway/apis/${apiId}/regenerate-token`)
}

export default apiClient
