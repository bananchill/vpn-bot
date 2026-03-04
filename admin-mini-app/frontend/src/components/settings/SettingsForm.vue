<script setup>
import { reactive, watch, computed } from 'vue'
import WebApp from '@twa-dev/sdk'
import ConnectionStatus from './ConnectionStatus.vue'

const props = defineProps({
  /** Current settings from the store (reactive object) */
  settings: {
    type: Object,
    required: true,
  },
  /** Connection status object from the store */
  connectionStatus: {
    type: Object,
    required: true,
  },
  /** Whether the form is currently being saved */
  saving: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['save', 'check-connection'])

// Local form state -- populated from props.settings on changes
const form = reactive({
  panel_url: '',
  panel_sub_url: '',
  panel_username: '',
  panel_password: '',
  owner_id: null,
  client_bot_token: '',
})

/**
 * Sync incoming settings into the local form.
 * Password fields stay empty: users enter a new value only when changing.
 */
watch(
  () => props.settings,
  (s) => {
    form.panel_url = s.panel_url || ''
    form.panel_sub_url = s.panel_sub_url || ''
    form.panel_username = s.panel_username || ''
    // Password fields are never populated; the placeholder shows masking
    form.panel_password = ''
    form.owner_id = s.owner_id
    form.client_bot_token = ''
  },
  { immediate: true, deep: true },
)

/** Format updated_at timestamp */
const lastUpdatedLabel = computed(() => {
  if (!props.settings.updated_at) return null
  const d = new Date(props.settings.updated_at)
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

/**
 * Build a partial payload containing only changed (non-empty) fields
 * and emit the save event.
 */
function handleSave() {
  const payload = {}

  if (form.panel_url) payload.panel_url = form.panel_url
  if (form.panel_sub_url) payload.panel_sub_url = form.panel_sub_url
  if (form.panel_username) payload.panel_username = form.panel_username
  if (form.panel_password) payload.panel_password = form.panel_password
  if (form.owner_id != null) payload.owner_id = Number(form.owner_id)
  if (form.client_bot_token) payload.client_bot_token = form.client_bot_token

  if (Object.keys(payload).length === 0) return

  WebApp.HapticFeedback?.impactOccurred?.('light')
  emit('save', payload)
}

function handleCheckConnection() {
  WebApp.HapticFeedback?.impactOccurred?.('light')
  emit('check-connection')
}
</script>

<template>
  <form
    class="space-y-5"
    @submit.prevent="handleSave"
  >
    <!-- Connection status card at TOP -->
    <div class="bg-white rounded-2xl p-4 shadow-soft">
      <div class="flex items-center justify-between">
        <ConnectionStatus
          :checked="connectionStatus.checked"
          :checking="connectionStatus.checking"
          :success="connectionStatus.success"
          :message="connectionStatus.message"
          :response-time-ms="connectionStatus.responseTimeMs"
        />
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-medium text-tg-button bg-tg-button/10 active:opacity-80"
          :disabled="connectionStatus.checking"
          @click="handleCheckConnection"
        >
          {{ connectionStatus.checking ? '...' : 'Тест' }}
        </button>
      </div>
    </div>

    <!-- Section: Panel connection -->
    <div>
      <p class="text-[11px] font-semibold text-tg-hint uppercase tracking-wider mb-2 px-4">
        Подключение к панели
      </p>
      <div class="bg-white rounded-2xl shadow-soft overflow-hidden">
        <!-- Panel URL -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">URL панели</label>
          <input
            v-model="form.panel_url"
            type="url"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            placeholder="https://panel.example.com:2096"
          >
        </div>
        <div class="border-t border-black/[0.06] mx-4" />

        <!-- Sub URL -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">URL подписки</label>
          <input
            v-model="form.panel_sub_url"
            type="url"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            placeholder="https://sub.example.com"
          >
        </div>
        <div class="border-t border-black/[0.06] mx-4" />

        <!-- Panel Username -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">Логин</label>
          <input
            v-model="form.panel_username"
            type="text"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            placeholder="admin"
            autocomplete="off"
          >
        </div>
        <div class="border-t border-black/[0.06] mx-4" />

        <!-- Panel Password -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">Пароль</label>
          <input
            v-model="form.panel_password"
            type="password"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            :placeholder="settings.has_password ? '••••••••' : 'Введите пароль'"
            autocomplete="new-password"
          >
          <p
            v-if="settings.has_password"
            class="mt-1 text-[11px] text-tg-hint"
          >
            Пароль задан. Оставьте пустым, чтобы не менять.
          </p>
        </div>
      </div>
    </div>

    <!-- Section: Telegram bot -->
    <div>
      <p class="text-[11px] font-semibold text-tg-hint uppercase tracking-wider mb-2 px-4">
        Telegram бот
      </p>
      <div class="bg-white rounded-2xl shadow-soft overflow-hidden">
        <!-- Owner ID -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">Owner ID</label>
          <input
            v-model.number="form.owner_id"
            type="number"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            placeholder="Telegram User ID"
          >
        </div>
        <div class="border-t border-black/[0.06] mx-4" />

        <!-- Client Bot Token -->
        <div class="px-4 py-3">
          <label class="block text-[11px] text-tg-hint mb-1">Токен клиентского бота</label>
          <input
            v-model="form.client_bot_token"
            type="password"
            class="w-full text-sm text-tg-text bg-transparent border-none outline-none placeholder:text-tg-hint/60"
            :placeholder="settings.client_bot_token_masked || 'Введите токен бота'"
            autocomplete="new-password"
          >
          <p
            v-if="settings.client_bot_token_masked"
            class="mt-1 text-[11px] text-tg-hint"
          >
            Токен задан ({{ settings.client_bot_token_masked }}).
          </p>
        </div>
      </div>
    </div>

    <!-- Save button -->
    <button
      type="submit"
      class="btn-primary"
      :disabled="saving"
    >
      {{ saving ? 'Сохранение...' : 'Сохранить настройки' }}
    </button>

    <!-- Last updated timestamp -->
    <p
      v-if="lastUpdatedLabel"
      class="text-xs text-tg-hint text-center pt-1"
    >
      Последнее обновление: {{ lastUpdatedLabel }}
    </p>
  </form>
</template>
