import { ref, reactive } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export const useSettingsStore = defineStore('settings', () => {
  const settings = reactive({
    panel_url: '',
    panel_sub_url: '',
    panel_username: '',
    has_password: false,
    owner_id: null,
    client_bot_token_masked: null,
    updated_at: null,
  })

  const loading = ref(false)
  const saving = ref(false)
  const error = ref(null)

  const connectionStatus = reactive({
    checked: false,
    checking: false,
    success: false,
    message: '',
    responseTimeMs: null,
  })

  /**
   * Load current settings from the API.
   * Populates the reactive settings object.
   */
  async function fetchSettings() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/settings')
      Object.assign(settings, data)
    } catch (err) {
      error.value = err.userMessage || 'Не удалось загрузить настройки'
    } finally {
      loading.value = false
    }
  }

  /**
   * Send a partial update to the API.
   * Only non-empty fields are transmitted.
   *
   * @param {Object} payload - Fields to update (see SettingsUpdate schema)
   */
  async function updateSettings(payload) {
    saving.value = true
    error.value = null
    try {
      const { data } = await api.put('/settings', payload)
      Object.assign(settings, data)
      return data
    } catch (err) {
      error.value = err.userMessage || 'Failed to save settings'
      throw err
    } finally {
      saving.value = false
    }
  }

  /**
   * Ask the backend to test panel connectivity with the stored credentials.
   * Updates the connectionStatus reactive object.
   */
  async function checkConnection() {
    connectionStatus.checking = true
    connectionStatus.checked = false
    error.value = null
    try {
      const { data } = await api.post('/settings/check')
      connectionStatus.success = data.success
      connectionStatus.message = data.message
      connectionStatus.responseTimeMs = data.response_time_ms
      connectionStatus.checked = true
    } catch (err) {
      connectionStatus.success = false
      connectionStatus.message = err.userMessage || 'Не удалось проверить соединение'
      connectionStatus.responseTimeMs = null
      connectionStatus.checked = true
    } finally {
      connectionStatus.checking = false
    }
  }

  return {
    settings,
    loading,
    saving,
    error,
    connectionStatus,
    fetchSettings,
    updateSettings,
    checkConnection,
  }
})
