import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/editor',
      name: 'editor',
      component: () => import('../views/EditorView.vue'),
    },
    {
      path: '/lineage',
      name: 'lineage',
      component: () => import('../views/LineageView.vue'),
    },
    {
      path: '/metadata',
      name: 'metadata',
      component: () => import('../views/MetadataView.vue'),
    },
    {
      path: '/git',
      name: 'git',
      component: () => import('../views/GitView.vue'),
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
  ],
})

export default router
