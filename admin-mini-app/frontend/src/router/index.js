import { createRouter, createWebHistory } from 'vue-router'
import WebApp from '@twa-dev/sdk'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Главная' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Настройки' },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('@/views/UsersListView.vue'),
    meta: { title: 'Пользователи' },
  },
  {
    path: '/users/:id',
    name: 'user-detail',
    component: () => import('@/views/UserDetailView.vue'),
    meta: { title: 'Пользователь' },
  },
  {
    path: '/promos',
    name: 'promos',
    component: () => import('@/views/PromosListView.vue'),
    meta: { title: 'Промокоды' },
  },
  {
    path: '/promos/create',
    name: 'promo-create',
    component: () => import('@/views/PromoCreateView.vue'),
    meta: { title: 'Новый промокод' },
  },
  {
    path: '/promos/:id',
    name: 'promo-detail',
    component: () => import('@/views/PromoDetailView.vue'),
    meta: { title: 'Промокод' },
  },
  {
    path: '/logs',
    name: 'logs',
    component: () => import('@/views/LogsView.vue'),
    meta: { title: 'Логи' },
  },
  {
    path: '/admins',
    name: 'admins',
    component: () => import('@/views/AdminsView.vue'),
    meta: { title: 'Админы' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Track previous BackButton handler so we can remove it
 * before attaching a new one (prevents handler stacking).
 */
let backButtonHandler = null

router.afterEach((to) => {
  // Remove stale handler to avoid duplicate navigation triggers
  if (backButtonHandler) {
    WebApp.BackButton.offClick(backButtonHandler)
    backButtonHandler = null
  }

  if (to.path === '/') {
    WebApp.BackButton.hide()
  } else {
    backButtonHandler = () => router.back()
    WebApp.BackButton.onClick(backButtonHandler)
    WebApp.BackButton.show()
  }
})

export default router
