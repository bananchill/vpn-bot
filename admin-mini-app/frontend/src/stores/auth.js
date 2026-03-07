import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import WebApp from '@twa-dev/sdk'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const initData = ref('')

  /**
   * Extract user info from the Telegram WebApp SDK.
   * Called once on app mount.
   */
  function initialize() {
    initData.value = WebApp.initData || ''

    if (WebApp.initDataUnsafe?.user) {
      const tgUser = WebApp.initDataUnsafe.user
      user.value = {
        id: tgUser.id,
        firstName: tgUser.first_name || '',
        lastName: tgUser.last_name || '',
        username: tgUser.username || '',
        languageCode: tgUser.language_code || 'ru',
        photoUrl: tgUser.photo_url || null,
      }
    }

    // Fallback: when running outside Telegram (no initData), use mock admin
    if (!initData.value) {
      initData.value = 'mock'
      user.value = {
        id: 123456789,
        firstName: 'Админ',
        lastName: '',
        username: 'admin',
        languageCode: 'ru',
        photoUrl: null,
      }
    }
  }

  const isAuthenticated = computed(() => !!initData.value)

  const displayName = computed(() => {
    if (!user.value) return ''
    const parts = [user.value.firstName, user.value.lastName].filter(Boolean)
    return parts.join(' ')
  })

  return {
    user,
    initData,
    isAuthenticated,
    displayName,
    initialize,
  }
})
