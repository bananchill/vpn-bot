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
    bg: '#e3f2fd',
  },
  {
    label: 'Доход за месяц',
    value: formatNumber(dashboardStore.stats.paid_users),
    emoji: '\uD83D\uDCB0',
    bg: '#f3e5f5',
  },
  {
    label: 'Истекают скоро',
    value: formatNumber(dashboardStore.stats.expiring_soon),
    emoji: '\u231B',
    bg: '#fff3e0',
  },
  {
    label: 'Активных конфигов',
    value: formatNumber(dashboardStore.stats.active_configs),
    emoji: '\uD83D\uDD11',
    bg: '#e8f5e9',
  },
])

const quickActions = [
  {
    title: 'Пользователи',
    description: 'Управление',
    path: '/users',
    gradient: 'linear-gradient(135deg, #667eea, #764ba2)',
    emoji: '\uD83D\uDC65',
  },
  {
    title: 'Настройки',
    description: 'Конфигурация',
    path: '/settings',
    gradient: 'linear-gradient(135deg, #f093fb, #f5576c)',
    emoji: '\u2699\uFE0F',
  },
  {
    title: 'Промокоды',
    description: 'Скидки',
    path: '/promos',
    gradient: 'linear-gradient(135deg, #4facfe, #00f2fe)',
    emoji: '\uD83C\uDFF7\uFE0F',
  },
  {
    title: 'Логи',
    description: 'Журнал',
    path: '/logs',
    gradient: 'linear-gradient(135deg, #43e97b, #38f9d7)',
    emoji: '\uD83D\uDCCB',
  },
]

/** Event icon backgrounds */
const eventIconBg = {
  '\u2705': '#e8f5e9',
  '\uD83D\uDD04': '#e3f2fd',
  '\u26A0\uFE0F': '#fff3e0',
}

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
  <div class="px-4 py-5 space-y-5" style="background: #f5f5f7; min-height: 100vh;">
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
        <p class="text-lg font-semibold" style="color: #1a1a2e;">
          Добро пожаловать!
        </p>
        <p class="text-sm" style="color: #8e8e93;">
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
        <p class="text-[26px] font-bold" style="color: #1a1a2e;">
          Привет, {{ greeting }}!
        </p>
        <p class="text-[14px] mt-0.5" style="color: #8e8e93;">
          Вот что происходит с вашим VPN
        </p>
      </div>

      <!-- Connection badge -->
      <div
        v-if="settingsStore.connectionStatus.checked || settingsStore.connectionStatus.checking"
        class="inline-flex items-center gap-2 px-3 py-1.5 rounded-[20px] text-[13px] font-medium"
        :style="{
          backgroundColor: isConnected ? '#e8f5e9' : settingsStore.connectionStatus.checking ? '#e3f2fd' : '#fce4ec',
          color: isConnected ? '#2e7d32' : settingsStore.connectionStatus.checking ? '#1565c0' : '#c62828',
        }"
      >
        <span
          class="w-2 h-2 rounded-[4px]"
          :style="{
            backgroundColor: isConnected ? '#4caf50' : settingsStore.connectionStatus.checking ? '#007aff' : '#c62828',
            opacity: isConnected ? 0.42 : 1,
          }"
          :class="settingsStore.connectionStatus.checking ? 'animate-pulse' : ''"
        />
        <span>{{ connectionLabel }}</span>
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
      <div v-if="!dashboardStore.error" class="grid grid-cols-2 gap-[12px]">
        <div
          v-for="stat in statCards"
          :key="stat.label"
          class="bg-white rounded-[16px] p-[16px]"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <div
            class="w-[36px] h-[36px] rounded-[10px] flex items-center justify-center text-[18px]"
            :style="{ backgroundColor: stat.bg }"
          >
            {{ stat.emoji }}
          </div>
          <p class="text-[24px] font-bold leading-tight mt-2.5" style="color: #1a1a2e;">
            {{ dashboardStore.loading ? '-' : stat.value }}
          </p>
          <p class="text-[13px] mt-0.5" style="color: #8e8e93;">
            {{ stat.label }}
          </p>
        </div>
      </div>

      <!-- Quick actions 2x2 -->
      <div>
        <p class="text-[18px] font-semibold mb-3" style="color: #1a1a2e;">
          Быстрые действия
        </p>
        <div class="grid grid-cols-2 gap-[12px]">
          <button
            v-for="action in quickActions"
            :key="action.path"
            class="bg-white rounded-[16px] p-[16px] flex flex-col gap-3 text-left active:opacity-80 transition-opacity"
            style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
            @click="navigateTo(action.path)"
          >
            <div
              class="w-[40px] h-[40px] rounded-[12px] flex items-center justify-center text-[18px]"
              :style="{ background: action.gradient }"
            >
              <span class="brightness-0 invert">{{ action.emoji }}</span>
            </div>
            <div>
              <p class="text-[15px] font-semibold" style="color: #1a1a2e;">{{ action.title }}</p>
              <p class="text-[12px] mt-0.5" style="color: #8e8e93;">{{ action.description }}</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Recent events -->
      <div v-if="dashboardStore.recentEvents.length">
        <p class="text-[18px] font-semibold mb-3" style="color: #1a1a2e;">
          Последние события
        </p>
        <div
          class="bg-white rounded-[16px] overflow-hidden"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <div
            v-for="(event, idx) in dashboardStore.recentEvents"
            :key="idx"
            class="flex items-center gap-3 px-4 py-3"
            :class="idx < dashboardStore.recentEvents.length - 1 ? 'border-b border-black/[0.06]' : ''"
          >
            <div
              class="w-[36px] h-[36px] rounded-[10px] flex items-center justify-center text-[16px] shrink-0"
              :style="{ backgroundColor: eventIconBg[event.emoji] || '#f5f5f7' }"
            >
              {{ event.emoji }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-[14px] font-medium truncate" style="color: #1a1a2e;">{{ event.title }}</p>
              <p class="text-[12px]" style="color: #8e8e93;">{{ event.time_ago }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
