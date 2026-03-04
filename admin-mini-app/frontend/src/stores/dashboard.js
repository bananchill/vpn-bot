import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = reactive({
    total_users: 0,
    paid_users: 0,
    expiring_soon: 0,
    active_configs: 0,
  })

  const recentEvents = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/dashboard/stats')
      Object.assign(stats, data)
    } catch (err) {
      error.value = err.userMessage || 'Не удалось загрузить статистику'
    } finally {
      loading.value = false
    }
  }

  async function fetchRecentEvents() {
    try {
      const { data } = await api.get('/dashboard/events')
      recentEvents.value = data.items || []
    } catch {
      // Endpoint may not exist yet — silently ignore
      recentEvents.value = []
    }
  }

  return {
    stats,
    recentEvents,
    loading,
    error,
    fetchStats,
    fetchRecentEvents,
  }
})
