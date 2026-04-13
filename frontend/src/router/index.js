import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('@/views/Models.vue')
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('@/views/Data.vue')
  },
  {
    path: '/detection',
    name: 'Detection',
    component: () => import('@/views/Detection.vue')
  },
  {
    path: '/results',
    name: 'Results',
    component: () => import('@/views/Results.vue')
  },
  {
    path: '/results/:id',
    name: 'ResultDetail',
    component: () => import('@/views/ResultDetail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
