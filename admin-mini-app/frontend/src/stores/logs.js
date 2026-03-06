import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export const useLogsStore = defineStore('logs', () => {
  // -- state ------------------------------------------------------------------

  const items = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const pages = ref(1)
  const loading = ref(false)
  const error = ref(null)

  const actionFilter = ref(null)
  const availableActions = ref([])

  // -- actions ----------------------------------------------------------------

  async function fetchLogs(params = {}) {
    loading.value = true
    error.value = null

    try {
      const query = {
        page: params.page ?? page.value,
        per_page: params.per_page ?? perPage.value,
      }

      const action = params.action !== undefined ? params.action : actionFilter.value
      if (action) {
        query.action = action
      }

      if (params.admin_id) {
        query.admin_id = params.admin_id
      }

      const { data } = await api.get('/logs', { params: query })

      items.value = data.items
      total.value = data.total
      page.value = data.page
      perPage.value = data.per_page
      pages.value = Math.ceil(data.total / data.per_page) || 1

      // Store available actions from the first response
      if (data.available_actions && data.available_actions.length > 0) {
        availableActions.value = data.available_actions
      }
    } catch (err) {
      error.value = err.userMessage || 'Не удалось загрузить логи'
    } finally {
      loading.value = false
    }
  }

  function setActionFilter(action) {
    actionFilter.value = action || null
    page.value = 1
    fetchLogs()
  }

  function goToPage(newPage) {
    page.value = newPage
    fetchLogs()
  }

  return {
    // state
    items,
    total,
    page,
    perPage,
    pages,
    loading,
    error,
    actionFilter,
    availableActions,

    // actions
    fetchLogs,
    setActionFilter,
    goToPage,
  }
})
