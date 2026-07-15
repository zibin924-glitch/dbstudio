import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || 'Request failed'
    ElMessage.error(message)
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

export default apiClient
