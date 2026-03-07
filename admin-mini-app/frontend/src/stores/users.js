import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export const useUsersStore = defineStore('users', () => {
  // -- state ----------------------------------------------------------------

  const users = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const pages = ref(1)
  const loading = ref(false)
  const error = ref(null)

  const filters = reactive({
    search: '',
    is_paid: null,
    subscription: null,
  })

  const sort = reactive({
    sort_by: 'created_at',
    sort_order: 'desc',
  })

  // Current user detail state
  const currentUser = ref(null)
  const loadingDetail = ref(false)
  const detailError = ref(null)

  // -- computed -------------------------------------------------------------

  const activeFilterLabel = computed(() => {
    if (filters.is_paid === true) return 'paid'
    if (filters.is_paid === false) return 'unpaid'
    if (filters.subscription === 'expiring_7d') return 'expiring'
    return 'all'
  })

  // -- actions: users list --------------------------------------------------

  /**
   * Fetch users from the API with current filters, sort, and pagination.
   * Merges explicit params so callers can override individual fields.
   */
  async function fetchUsers(params = {}) {
    loading.value = true
    error.value = null

    try {
      const query = {
        page: params.page ?? page.value,
        per_page: params.per_page ?? perPage.value,
        sort_by: sort.sort_by,
        sort_order: sort.sort_order,
      }

      // Only include non-empty filters to keep the URL clean
      if (filters.search) query.search = filters.search
      if (filters.is_paid !== null) query.is_paid = filters.is_paid
      if (filters.subscription) query.subscription = filters.subscription

      const { data } = await api.get('/users', { params: query })

      users.value = data.items
      total.value = data.total
      page.value = data.page
      perPage.value = data.per_page
      pages.value = data.pages
    } catch (err) {
      error.value = err.userMessage || 'Не удалось загрузить список пользователей'
    } finally {
      loading.value = false
    }
  }

  /**
   * Apply a named filter preset and reset to page 1.
   * Presets: 'all', 'paid', 'unpaid', 'expiring'
   */
  function setFilter(preset) {
    // Reset all filters first
    filters.is_paid = null
    filters.subscription = null

    if (preset === 'paid') {
      filters.is_paid = true
    } else if (preset === 'unpaid') {
      filters.is_paid = false
    } else if (preset === 'expiring') {
      filters.subscription = 'expiring_7d'
    }

    page.value = 1
    fetchUsers()
  }

  /**
   * Update the search term and reset to page 1.
   * Called from SearchInput with debounce on the view side.
   */
  function setSearch(term) {
    filters.search = term
    page.value = 1
    fetchUsers()
  }

  function resetFilters() {
    filters.search = ''
    filters.is_paid = null
    filters.subscription = null
    sort.sort_by = 'created_at'
    sort.sort_order = 'desc'
    page.value = 1
  }

  function goToPage(newPage) {
    page.value = newPage
    fetchUsers()
  }

  // -- actions: user detail -------------------------------------------------

  async function fetchUserDetail(userId) {
    loadingDetail.value = true
    detailError.value = null

    try {
      const { data } = await api.get(`/users/${userId}`)
      currentUser.value = data
      return data
    } catch (err) {
      detailError.value = err.userMessage || 'Не удалось загрузить данные пользователя'
    } finally {
      loadingDetail.value = false
    }
  }

  async function toggleBlock(userId, isBlocked) {
    const { data } = await api.patch(`/users/${userId}/block`, {
      is_blocked: isBlocked,
    })

    // Refresh the current user detail if we are viewing this user
    if (currentUser.value && currentUser.value.id === userId) {
      currentUser.value.is_blocked = data.is_blocked
    }

    return data
  }

  async function updateNote(userId, note) {
    await api.patch(`/users/${userId}/note`, { note })

    if (currentUser.value && currentUser.value.id === userId) {
      currentUser.value.admin_note = note
    }
  }

  async function extendSubscription(userId, days) {
    const { data } = await api.patch(`/users/${userId}/extend`, { days })

    // Replace the entire current user to pick up computed fields
    if (currentUser.value && currentUser.value.id === userId) {
      currentUser.value = data
    }

    return data
  }

  // -- actions: config toggles ----------------------------------------------

  async function toggleConfig(configId, enabled) {
    const { data } = await api.patch(`/configs/${configId}/toggle`, { enabled })

    // Update the config in-place inside currentUser
    if (currentUser.value) {
      const idx = currentUser.value.configs.findIndex((c) => c.id === configId)
      if (idx !== -1) {
        currentUser.value.configs[idx].is_enabled = data.is_enabled
      }
    }

    return data
  }

  async function toggleAllConfigs(userId, enabled) {
    const { data } = await api.post(`/users/${userId}/configs/toggle-all`, {
      enabled,
    })

    // Update all configs in-place
    if (currentUser.value && currentUser.value.id === userId) {
      currentUser.value.configs.forEach((c) => {
        c.is_enabled = enabled
      })
    }

    return data
  }

  return {
    // state
    users,
    total,
    page,
    perPage,
    pages,
    loading,
    error,
    filters,
    sort,
    currentUser,
    loadingDetail,
    detailError,

    // computed
    activeFilterLabel,

    // actions: list
    fetchUsers,
    setFilter,
    setSearch,
    resetFilters,
    goToPage,

    // actions: detail
    fetchUserDetail,
    toggleBlock,
    updateNote,
    extendSubscription,

    // actions: configs
    toggleConfig,
    toggleAllConfigs,
  }
})
