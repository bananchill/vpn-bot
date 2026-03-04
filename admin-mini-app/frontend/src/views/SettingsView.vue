<script setup>
import { onMounted } from 'vue'
import WebApp from '@twa-dev/sdk'
import { useSettingsStore } from '@/stores/settings'
import SettingsForm from '@/components/settings/SettingsForm.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const store = useSettingsStore()

onMounted(async () => {
  await store.fetchSettings()
  // Auto-check connection if panel URL is configured
  if (store.settings.panel_url) {
    store.checkConnection()
  }
})

async function handleSave(payload) {
  try {
    await store.updateSettings(payload)
    WebApp.HapticFeedback?.notificationOccurred?.('success')
    WebApp.showAlert?.('Настройки сохранены')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  }
}

function handleCheckConnection() {
  store.checkConnection()
}
</script>

<template>
  <div class="px-4 py-5">
    <LoadingSpinner
      v-if="store.loading"
      message="Загрузка настроек..."
    />

    <div
      v-else-if="store.error && !store.settings.panel_url"
      class="card"
    >
      <p class="text-sm text-red-500 text-center py-6">
        {{ store.error }}
      </p>
    </div>

    <SettingsForm
      v-else
      :settings="store.settings"
      :connection-status="store.connectionStatus"
      :saving="store.saving"
      @save="handleSave"
      @check-connection="handleCheckConnection"
    />
  </div>
</template>
