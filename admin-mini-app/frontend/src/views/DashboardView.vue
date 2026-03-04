<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useDashboardStore } from '@/stores/dashboard'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const router = useRouter()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const dashboardStore = useDashboardStore()

const hasSettings = computed(() => !!settingsStore.settings.panel_url)

const greeting = computed(() => authStore.user?.firstName || 'Админ')

const connectionLabel = computed(() => {
  const cs = settingsStore.connectionStatus
  if (cs.checking) return 'Проверка...'
  if (cs.checked && cs.success) {
    return cs.responseTimeMs != null
      ? `Панель подключена \u00b7 ${cs.responseTimeMs}ms`
      : 'Панель подключена'
  }
  if (cs.checked && !cs.success) return 'Ошибка подключения'
  return 'Не проверено'
})

const isConnected = computed(() =>
  settingsStore.connectionStatus.checked && settingsStore.connectionStatus.success,
)

function formatNumber(value) {
  if (value == null) return '0'
  return Number(value).toLocaleString('en-US')
}

const statCards = computed(() => [
  {
    label: 'Пользователей',
    value: formatNumber(dashboardStore.stats.total_users),
    emoji: '\uD83D\uDC65',
    bg: 'bg-blue-50',
  },
  {
    label: 'Оплачено',
    value: formatNumber(dashboardStore.stats.paid_users),
    emoji: '\uD83D\uDCB0',
    bg: 'bg-green-50',
  },
  {
    label: 'Истекают скоро',
    value: formatNumber(dashboardStore.stats.expiring_soon),
    emoji: '\u231B',
    bg: 'bg-orange-50',
  },
  {
    label: 'Активных конфигов',
    value: formatNumber(dashboardStore.stats.active_configs),
    emoji: '\uD83D\uDD11',
    bg: 'bg-purple-50',
  },
])

const quickActions = [
  {
    title: 'Пользователи',
    description: 'Управление аккаунтами',
    path: '/users',
    bg: 'bg-green-500',
    emoji: '\uD83D\uDC65',
  },
  {
    title: 'Настройки',
    description: 'Конфигурация панели',
    path: '/settings',
    bg: 'bg-orange-400',
    emoji: '\u2699\uFE0F',
  },
  {
    title: 'Промокоды',
    description: 'Скидки и акции',
    path: '/promos',
    bg: 'bg-blue-500',
    emoji: '\uD83C\uDFF7\uFE0F',
  },
  {
    title: 'Логи',
    description: 'Журнал действий',
    path: '/logs',
    bg: 'bg-green-400',
    emoji: '\uD83D\uDCCB',
  },
]

onMounted(async () => {
  try {
    await settingsStore.fetchSettings()
  } catch {
    // fetchSettings already stores the error in the store
  }

  if (hasSettings.value) {
    settingsStore.checkConnection()
    dashboardStore.fetchStats()
    dashboardStore.fetchRecentEvents()
  }
})

function navigateTo(path) {
  WebApp.HapticFeedback?.impactOccurred?.('light')
  router.push(path)
}
</script>

<template>
  <div class="px-4 py-5 space-y-5">
    <!-- Loading state -->
    <LoadingSpinner
      v-if="settingsStore.loading"
      message="Загрузка..."
    />

    <!-- Error loading settings -->
    <div
      v-else-if="settingsStore.error"
      class="card text-center py-10 space-y-4"
    >
      <p class="text-sm text-red-500">{{ settingsStore.error }}</p>
      <button
        class="btn-primary"
        @click="settingsStore.fetchSettings()"
      >
        Повторить
      </button>
    </div>

    <!-- Onboarding: shown when no panel settings configured yet -->
    <div
      v-else-if="!hasSettings"
      class="card text-center py-10 space-y-4"
    >
      <p class="text-4xl">&#x1F44B;</p>
      <div class="space-y-1">
        <p class="text-lg font-semibold text-tg-text">
          Добро пожаловать!
        </p>
        <p class="text-sm text-tg-hint">
          Настройте подключение к панели, чтобы начать работу.
        </p>
      </div>
      <button
        class="btn-primary"
        @click="navigateTo('/settings')"
      >
        Перейти к настройкам &rarr;
      </button>
    </div>

    <!-- Dashboard: shown when settings are configured -->
    <template v-else>
      <!-- Greeting section -->
      <div>
        <p class="text-2xl font-bold text-tg-text">
          Привет, {{ greeting }}!
        </p>
        <p class="text-sm text-tg-hint mt-0.5">
          Вот что происходит с вашим VPN-сервисом
        </p>
      </div>

      <!-- Connection badge -->
      <div
        v-if="settingsStore.connectionStatus.checked || settingsStore.connectionStatus.checking"
        class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white shadow-soft text-xs font-medium"
      >
        <span
          class="w-2 h-2 rounded-full"
          :class="isConnected ? 'bg-[#34c759]' : settingsStore.connectionStatus.checking ? 'bg-tg-button animate-pulse' : 'bg-red-500'"
        />
        <span class="text-tg-text">{{ connectionLabel }}</span>
      </div>

      <!-- Dashboard error -->
      <div
        v-if="dashboardStore.error"
        class="card"
      >
        <p class="text-sm text-red-500 text-center py-2">
          {{ dashboardStore.error }}
        </p>
      </div>

      <!-- Stats grid 2x2 -->
      <div v-if="!dashboardStore.error" class="grid grid-cols-2 gap-3">
        <div
          v-for="stat in statCards"
          :key="stat.label"
          class="card flex items-start gap-3"
        >
          <div
            class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-lg"
            :class="[stat.bg]"
          >
            {{ stat.emoji }}
          </div>
          <div class="min-w-0">
            <p class="text-xl font-bold text-tg-text leading-tight">
              {{ dashboardStore.loading ? '-' : stat.value }}
            </p>
            <p class="text-[11px] text-tg-hint mt-0.5 leading-tight">
              {{ stat.label }}
            </p>
          </div>
        </div>
      </div>

      <!-- Quick actions 2x2 -->
      <div>
        <p class="text-[11px] font-semibold text-tg-hint uppercase tracking-wider mb-2">
          Быстрые действия
        </p>
        <div class="grid grid-cols-2 gap-3">
          <button
            v-for="action in quickActions"
            :key="action.path"
            class="card flex flex-col gap-3 text-left active:opacity-80 transition-opacity"
            @click="navigateTo(action.path)"
          >
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
              :class="action.bg"
            >
              {{ action.emoji }}
            </div>
            <div>
              <p class="text-sm font-semibold text-tg-text">{{ action.title }}</p>
              <p class="text-[11px] text-tg-hint mt-0.5">{{ action.description }}</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Recent events -->
      <div v-if="dashboardStore.recentEvents.length">
        <p class="text-[11px] font-semibold text-tg-hint uppercase tracking-wider mb-2">
          Последние события
        </p>
        <div class="card divide-y divide-black/[0.06]">
          <div
            v-for="(event, idx) in dashboardStore.recentEvents"
            :key="idx"
            class="flex items-center gap-3 px-4 py-3"
          >
            <span class="text-lg shrink-0">{{ event.emoji }}</span>
            <div class="min-w-0 flex-1">
              <p class="text-sm text-tg-text truncate">{{ event.title }}</p>
              <p class="text-[11px] text-tg-hint">{{ event.time_ago }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
