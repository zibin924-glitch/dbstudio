import { defineStore } from 'pinia'
import {
  executeQuery as apiExecuteQuery,
  exportResults as apiExportResults,
  getHistory as apiGetHistory,
  toggleFavorite as apiToggleFavorite
} from '@/api/index.js'

let tabIdCounter = 1

// sessionStorage 键名常量
const TABS_STORAGE_KEY = 'dbstudio_queryTabs'
const ACTIVE_TAB_KEY = 'dbstudio_activeTabId'

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
      // 持久化标签页状态
      this._persistTabs()
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
        // 持久化标签页状态
        this._persistTabs()
        return
      }
      this.tabs.splice(index, 1)
      if (this.activeTabId === tabId) {
        const newIndex = Math.min(index, this.tabs.length - 1)
        this.activeTabId = this.tabs[newIndex].id
      }
      // 持久化标签页状态
      this._persistTabs()
    },

    setActiveTab(tabId) {
      this.activeTabId = tabId
      // 持久化标签页状态
      this._persistTabs()
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
        // 执行查询后持久化标签页中的 SQL 文本
        this._persistTabs()
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
    },

    // 持久化标签页到 sessionStorage（只保存轻量数据，不保存查询结果）
    _persistTabs() {
      try {
        const tabsData = this.tabs.map(t => ({
          id: t.id,
          name: t.name,
          sql: t.sql
        }))
        sessionStorage.setItem(TABS_STORAGE_KEY, JSON.stringify(tabsData))
        sessionStorage.setItem(ACTIVE_TAB_KEY, JSON.stringify(this.activeTabId))
        // 同步更新 tabIdCounter，避免恢复后 ID 冲突
        const maxId = Math.max(...this.tabs.map(t => t.id), 0)
        if (tabIdCounter <= maxId) {
          tabIdCounter = maxId + 1
        }
      } catch (e) {
        console.warn('Failed to persist query tabs:', e)
      }
    },

    // 从 sessionStorage 恢复标签页状态
    restoreTabs() {
      try {
        const savedTabs = sessionStorage.getItem(TABS_STORAGE_KEY)
        const savedActiveId = sessionStorage.getItem(ACTIVE_TAB_KEY)
        if (savedTabs) {
          const parsedTabs = JSON.parse(savedTabs)
          if (Array.isArray(parsedTabs) && parsedTabs.length > 0) {
            // 恢复标签页（只恢复 id, name, sql，其余字段使用默认值）
            this.tabs = parsedTabs.map(t => ({
              id: t.id,
              name: t.name || `Query ${t.id}`,
              sql: t.sql || '',
              results: null,
              columns: [],
              rows: [],
              total: 0,
              page: 1,
              pageSize: 50,
              durationMs: null,
              loading: false,
              error: null
            }))
            // 更新 tabIdCounter 以避免新标签 ID 冲突
            const maxId = Math.max(...this.tabs.map(t => t.id), 0)
            tabIdCounter = maxId + 1

            // 恢复激活的标签页
            if (savedActiveId) {
              const activeId = JSON.parse(savedActiveId)
              if (this.tabs.some(t => t.id === activeId)) {
                this.activeTabId = activeId
              }
            }
          }
        }
      } catch (e) {
        console.warn('Failed to restore query tabs:', e)
      }
    }
  }
})
