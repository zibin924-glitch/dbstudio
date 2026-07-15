import { createRouter, createWebHistory } from 'vue-router'
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
    meta: { title: 'Structure Explorer' }
  },
  {
    path: '/query',
    name: 'QueryConsole',
    component: QueryConsole,
    meta: { title: 'SQL Console' }
  },
  {
    path: '/generator',
    name: 'Generator',
    component: Generator,
    meta: { title: 'Generator' }
  },
  {
    path: '/api-gateway',
    name: 'ApiGateway',
    component: ApiGateway,
    meta: { title: 'API Gateway' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'DBStudio'} - DBStudio`
  next()
})

export default router
