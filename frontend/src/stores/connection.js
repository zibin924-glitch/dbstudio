import { defineStore } from 'pinia'
import {
  getConnections,
  createConnection as apiCreateConnection,
  updateConnection as apiUpdateConnection,
  deleteConnection as apiDeleteConnection,
  testConnection as apiTestConnection
} from '@/api/index.js'

export const useConnectionStore = defineStore('connection', {
  state: () => ({
    connections: [],
    currentConnection: null,
    loading: false,
    groups: []
  }),

  getters: {
    groupedConnections(state) {
      const grouped = {}
      for (const conn of state.connections) {
        const group = conn.group_name || 'Default'
        if (!grouped[group]) {
          grouped[group] = []
        }
        grouped[group].push(conn)
      }
      return grouped
    },

    connectionOptions(state) {
      return state.connections.map(c => ({
        label: c.name,
        value: c.id
      }))
    }
  },

  actions: {
    async fetchConnections() {
      this.loading = true
      try {
        const response = await getConnections()
        this.connections = response.data || response
        const groupSet = new Set()
        for (const conn of this.connections) {
          groupSet.add(conn.group_name || 'Default')
        }
        this.groups = Array.from(groupSet)
      } catch (error) {
        console.error('Failed to fetch connections:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async createConnection(data) {
      this.loading = true
      try {
        const response = await apiCreateConnection(data)
        await this.fetchConnections()
        return response
      } catch (error) {
        console.error('Failed to create connection:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateConnection(id, data) {
      this.loading = true
      try {
        const response = await apiUpdateConnection(id, data)
        await this.fetchConnections()
        return response
      } catch (error) {
        console.error('Failed to update connection:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteConnection(id) {
      this.loading = true
      try {
        const response = await apiDeleteConnection(id)
        await this.fetchConnections()
        if (this.currentConnection && this.currentConnection.id === id) {
          // 删除的是当前连接，通过 setCurrentConnection 清除并更新 sessionStorage
          this.setCurrentConnection(null)
        }
        return response
      } catch (error) {
        console.error('Failed to delete connection:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async testConnection(data) {
      try {
        const response = await apiTestConnection(data)
        return response
      } catch (error) {
        console.error('Failed to test connection:', error)
        throw error
      }
    },

    setCurrentConnection(connection) {
      this.currentConnection = connection
      // 持久化当前连接 ID 到 sessionStorage
      try {
        if (connection && connection.id) {
          sessionStorage.setItem('dbstudio_currentConnectionId', JSON.stringify(connection.id))
        } else {
          sessionStorage.removeItem('dbstudio_currentConnectionId')
        }
      } catch (e) {
        // sessionStorage 不可用时忽略
        console.warn('Failed to persist connection state:', e)
      }
    },

    // 从 sessionStorage 恢复当前连接状态
    restoreState() {
      try {
        const savedId = sessionStorage.getItem('dbstudio_currentConnectionId')
        if (savedId) {
          const id = JSON.parse(savedId)
          // 在已加载的连接列表中查找匹配的连接
          const conn = this.connections.find(c => c.id === id)
          if (conn) {
            this.currentConnection = conn
          } else {
            // 连接已不存在，清除 sessionStorage
            sessionStorage.removeItem('dbstudio_currentConnectionId')
          }
        }
      } catch (e) {
        console.warn('Failed to restore connection state:', e)
      }
    }
  }
})
