import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export const usePromosStore = defineStore('promos', () => {
  // -- state: list ------------------------------------------------------------

  const promos = ref([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(20)
  const pages = ref(1)
  const loading = ref(false)
  const error = ref(null)

  // -- state: detail ----------------------------------------------------------

  const currentPromo = ref(null)
  const loadingDetail = ref(false)
  const detailError = ref(null)

  // -- state: usages ----------------------------------------------------------

  const usages = ref([])
  const usagesTotal = ref(0)
  const usagesPage = ref(1)
  const usagesPages = ref(1)
  const loadingUsages = ref(false)

  // -- actions: list ----------------------------------------------------------

  async function fetchPromos(params = {}) {
    loading.value = true
    error.value = null

    try {
      const query = {
        page: params.page ?? page.value,
        per_page: params.per_page ?? perPage.value,
      }

      if (params.is_active !== undefined && params.is_active !== null) {
        query.is_active = params.is_active
      }

      const { data } = await api.get('/promos', { params: query })

      promos.value = data.items
      total.value = data.total
      page.value = data.page
      perPage.value = data.per_page
      pages.value = Math.ceil(data.total / data.per_page) || 1
    } catch (err) {
      error.value = err.userMessage || 'Не удалось загрузить промокоды'
    } finally {
      loading.value = false
    }
  }

  function goToPage(newPage) {
    page.value = newPage
    fetchPromos()
  }

  // -- actions: detail --------------------------------------------------------

  async function fetchPromo(id) {
    loadingDetail.value = true
    detailError.value = null

    try {
      const { data } = await api.get(`/promos/${id}`)
      currentPromo.value = data
      return data
    } catch (err) {
      detailError.value = err.userMessage || 'Не удалось загрузить промокод'
    } finally {
      loadingDetail.value = false
    }
  }

  // -- actions: create --------------------------------------------------------

  async function createPromo(payload) {
    const { data } = await api.post('/promos', payload)
    return data
  }

  // -- actions: toggle --------------------------------------------------------

  async function togglePromo(id, isActive) {
    const { data } = await api.patch(`/promos/${id}/toggle`, {
      is_active: isActive,
    })

    // Update in-place if viewing this promo
    if (currentPromo.value && currentPromo.value.id === id) {
      currentPromo.value = data
    }

    // Update in list
    const idx = promos.value.findIndex((p) => p.id === id)
    if (idx !== -1) {
      promos.value[idx] = data
    }

    return data
  }

  // -- actions: delete --------------------------------------------------------

  async function deletePromo(id) {
    await api.delete(`/promos/${id}`)

    // Remove from list
    promos.value = promos.value.filter((p) => p.id !== id)
    total.value = Math.max(0, total.value - 1)

    if (currentPromo.value && currentPromo.value.id === id) {
      currentPromo.value = null
    }
  }

  // -- actions: usages --------------------------------------------------------

  async function fetchUsages(promoId, params = {}) {
    loadingUsages.value = true

    try {
      const query = {
        page: params.page ?? usagesPage.value,
        per_page: 20,
      }

      const { data } = await api.get(`/promos/${promoId}/usages`, {
        params: query,
      })

      usages.value = data.items
      usagesTotal.value = data.total
      usagesPage.value = data.page
      usagesPages.value = Math.ceil(data.total / (data.per_page || 20)) || 1
    } catch {
      usages.value = []
    } finally {
      loadingUsages.value = false
    }
  }

  // -- actions: generate code -------------------------------------------------

  async function generateCode() {
    const { data } = await api.get('/promos/generate-code')
    return data.code
  }

  return {
    // state: list
    promos,
    total,
    page,
    perPage,
    pages,
    loading,
    error,

    // state: detail
    currentPromo,
    loadingDetail,
    detailError,

    // state: usages
    usages,
    usagesTotal,
    usagesPage,
    usagesPages,
    loadingUsages,

    // actions
    fetchPromos,
    goToPage,
    fetchPromo,
    createPromo,
    togglePromo,
    deletePromo,
    fetchUsages,
    generateCode,
  }
})
