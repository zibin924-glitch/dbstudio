import { defineStore } from 'pinia'
import {
  executeQuery as apiExecuteQuery,
  exportResults as apiExportResults,
  getHistory as apiGetHistory,
  toggleFavorite as apiToggleFavorite
} from '@/api/index.js'

let tabIdCounter = 1

function createNewTab(name) {
  const id = tabIdCounter++
  return {
    id,
    name: name || `Query ${id}`,
    sql: '',
    results: null,
    columns: [],
    rows: [],
    total: 0,
    page: 1,
    pageSize: 50,
    durationMs: null,
    loading: false,
    error: null
  }
}

export const useQueryStore = defineStore('query', {
  state: () => ({
    tabs: [createNewTab('Query 1')],
    activeTabId: 1,
    history: [],
    historyLoading: false,
    historySearch: ''
  }),

  getters: {
    activeTab(state) {
      return state.tabs.find(t => t.id === state.activeTabId) || state.tabs[0]
    }
  },

  actions: {
    addTab(name) {
      const tab = createNewTab(name)
      this.tabs.push(tab)
      this.activeTabId = tab.id
      return tab
    },

    removeTab(tabId) {
      const index = this.tabs.findIndex(t => t.id === tabId)
      if (index === -1) return
      if (this.tabs.length === 1) {
        // Don't remove the last tab, just clear it
        this.tabs[0].sql = ''
        this.tabs[0].results = null
        this.tabs[0].columns = []
        this.tabs[0].rows = []
        this.tabs[0].total = 0
        this.tabs[0].durationMs = null
        this.tabs[0].error = null
        return
      }
      this.tabs.splice(index, 1)
      if (this.activeTabId === tabId) {
        const newIndex = Math.min(index, this.tabs.length - 1)
        this.activeTabId = this.tabs[newIndex].id
      }
    },

    setActiveTab(tabId) {
      this.activeTabId = tabId
    },

    async executeQuery(connectionId, sql, page = 1, pageSize = 50) {
      const tab = this.activeTab
      if (!tab) return

      tab.loading = true
      tab.error = null
      try {
        const response = await apiExecuteQuery({
          connection_id: connectionId,
          sql: sql,
          page: page,
          page_size: pageSize
        })
        const data = response.data || response
        tab.columns = data.columns || []
        tab.rows = data.rows || []
        tab.total = data.total || (data.rows ? data.rows.length : 0)
        tab.durationMs = data.duration_ms || null
        tab.page = page
        tab.pageSize = pageSize
        tab.results = data
        return data
      } catch (error) {
        const message = error.response?.data?.detail || error.message || 'Query execution failed'
        tab.error = message
        throw error
      } finally {
        tab.loading = false
      }
    },

    async exportResults(connectionId, sql, format) {
      try {
        const response = await apiExportResults({
          connection_id: connectionId,
          sql: sql,
          format: format
        })
        return response
      } catch (error) {
        console.error('Failed to export results:', error)
        throw error
      }
    },

    async fetchHistory(connectionId, search = '') {
      this.historyLoading = true
      try {
        const params = {}
        if (connectionId) params.connection_id = connectionId
        if (search) params.search = search
        const response = await apiGetHistory(params)
        this.history = response.data || response || []
      } catch (error) {
        console.error('Failed to fetch history:', error)
        this.history = []
      } finally {
        this.historyLoading = false
      }
    },

    async searchHistory(query) {
      this.historySearch = query
      await this.fetchHistory(null, query)
    },

    async toggleFavorite(historyId) {
      try {
        await apiToggleFavorite(historyId)
        const item = this.history.find(h => h.id === historyId)
        if (item) {
          item.is_favorite = !item.is_favorite
        }
      } catch (error) {
        console.error('Failed to toggle favorite:', error)
        throw error
      }
    }
  }
})
