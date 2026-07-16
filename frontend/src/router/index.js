import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useConnectionStore } from '@/stores/connection.js'
import Connections from '@/views/Connections.vue'
import Explorer from '@/views/Explorer.vue'
import QueryConsole from '@/views/QueryConsole.vue'
import Generator from '@/views/Generator.vue'
import ApiGateway from '@/views/ApiGateway.vue'

const routes = [
  {
    path: '/',
    redirect: '/connections'
  },
  {
    path: '/connections',
    name: 'Connections',
    component: Connections,
    meta: { title: 'Connections' }
  },
  {
    path: '/explorer',
    name: 'Explorer',
    component: Explorer,
    meta: { title: 'Structure Explorer', requiresConnection: true }
  },
  {
    path: '/query',
    name: 'QueryConsole',
    component: QueryConsole,
    meta: { title: 'SQL Console', requiresConnection: true }
  },
  {
    path: '/generator',
    name: 'Generator',
    component: Generator,
    meta: { title: 'Generator', requiresConnection: true }
  },
  {
    path: '/api-gateway',
    name: 'ApiGateway',
    component: ApiGateway,
    meta: { title: 'API Gateway', requiresConnection: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'DBStudio'} - DBStudio`

  // 路由守卫：需要连接才能访问的页面
  if (to.meta.requiresConnection) {
    // 延迟获取 Pinia store（需要在 app 初始化后使用）
    const connectionStore = useConnectionStore()
    // 如果连接列表为空，重定向到连接管理页面
    if (connectionStore.connections.length === 0) {
      ElMessage.info('请先创建数据库连接')
      next({ path: '/connections' })
      return
    }
  }

  next()
})

export default router
