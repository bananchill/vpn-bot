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
    <div
      class="bg-white rounded-[16px] h-[76px] px-[16px] flex items-center gap-[12px]"
      style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
    >
      <ConnectionStatus
        :checked="connectionStatus.checked"
        :checking="connectionStatus.checking"
        :success="connectionStatus.success"
        :message="connectionStatus.message"
        :response-time-ms="connectionStatus.responseTimeMs"
        class="flex-1 min-w-0"
      />
      <button
        type="button"
        class="rounded-[10px] h-[32px] px-[14px] py-[8px] text-[13px] font-medium active:opacity-80 shrink-0"
        style="background-color: #f5f5f7; color: #007aff;"
        :disabled="connectionStatus.checking"
        @click="handleCheckConnection"
      >
        {{ connectionStatus.checking ? '...' : 'Тест' }}
      </button>
    </div>

    <!-- Section: Panel connection -->
    <div>
      <p
        class="text-[13px] font-semibold uppercase mb-2 pl-[4px]"
        style="color: #8e8e93; letter-spacing: 0.5px;"
      >
        Подключение к панели
      </p>
      <div
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <!-- Panel URL -->
        <div class="px-[16px] pt-[12px] pb-px border-b border-black/[0.06]">
          <label class="block text-[12px]" style="color: #8e8e93;">URL панели</label>
          <input
            v-model="form.panel_url"
            type="url"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            placeholder="https://panel.example.com:2053"
          >
        </div>

        <!-- Sub URL -->
        <div class="px-[16px] pt-[12px] pb-px border-b border-black/[0.06]">
          <label class="block text-[12px]" style="color: #8e8e93;">URL подписки</label>
          <input
            v-model="form.panel_sub_url"
            type="url"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            placeholder="https://sub.example.com"
          >
        </div>

        <!-- Panel Username -->
        <div class="px-[16px] pt-[12px] pb-px border-b border-black/[0.06]">
          <label class="block text-[12px]" style="color: #8e8e93;">Логин</label>
          <input
            v-model="form.panel_username"
            type="text"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            placeholder="admin"
            autocomplete="off"
          >
        </div>

        <!-- Panel Password -->
        <div class="px-[16px] pt-[12px] pb-[12px]">
          <label class="block text-[12px]" style="color: #8e8e93;">Пароль</label>
          <input
            v-model="form.panel_password"
            type="password"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            :placeholder="settings.has_password ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' : 'Введите пароль'"
            autocomplete="new-password"
          >
        </div>
      </div>
    </div>

    <!-- Section: Telegram bot -->
    <div>
      <p
        class="text-[13px] font-semibold uppercase mb-2 pl-[4px]"
        style="color: #8e8e93; letter-spacing: 0.5px;"
      >
        Telegram бот
      </p>
      <div
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <!-- Owner ID -->
        <div class="px-[16px] pt-[12px] pb-px border-b border-black/[0.06]">
          <label class="block text-[12px]" style="color: #8e8e93;">Owner ID</label>
          <input
            v-model.number="form.owner_id"
            type="number"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            placeholder="Telegram User ID"
          >
        </div>

        <!-- Client Bot Token -->
        <div class="px-[16px] pt-[12px] pb-[12px]">
          <label class="block text-[12px]" style="color: #8e8e93;">Токен клиентского бота</label>
          <input
            v-model="form.client_bot_token"
            type="password"
            class="w-full text-[15px] bg-transparent border-none outline-none py-[5px]"
            style="color: #1a1a2e;"
            :placeholder="settings.client_bot_token_masked || 'Введите токен бота'"
            autocomplete="new-password"
          >
        </div>
      </div>
    </div>

    <!-- Save button -->
    <button
      type="submit"
      class="w-full rounded-[14px] h-[52px] p-[16px] text-[16px] font-semibold text-white active:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
      style="background-color: #007aff;"
      :disabled="saving"
    >
      {{ saving ? 'Сохранение...' : 'Сохранить настройки' }}
    </button>

    <!-- Last updated timestamp -->
    <p
      v-if="lastUpdatedLabel"
      class="text-[12px] text-center pt-1"
      style="color: #8e8e93;"
    >
      Последнее обновление: {{ lastUpdatedLabel }}
    </p>
  </form>
</template>
