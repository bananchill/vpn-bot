<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  user: {
    type: Object,
    required: true,
  },
})

/** Gradient backgrounds for fallback avatars */
const gradients = [
  'from-indigo-500 to-purple-600',
  'from-blue-400 to-cyan-300',
  'from-pink-400 to-rose-500',
  'from-emerald-400 to-teal-300',
  'from-pink-500 to-yellow-300',
]

/** Compute a stable gradient index based on user id */
const gradientClass = computed(() => {
  const id = props.user.id || props.user.telegram_id || 0
  const index = Math.abs(id) % gradients.length
  return gradients[index]
})

const initials = computed(() => {
  const name = props.user.first_name || props.user.username || ''
  return name.charAt(0).toUpperCase() || '?'
})

const expiryLabel = computed(() => {
  if (!props.user.subscription_expires) return '-'
  const d = new Date(props.user.subscription_expires)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
  })
})

const paymentStatus = computed(() =>
  props.user.is_paid ? 'paid' : 'unpaid',
)

const telegramLink = computed(() =>
  `tg://user?id=${props.user.telegram_id}`,
)

const configsCount = computed(() =>
  props.user.configs ? props.user.configs.length : 0,
)

const daysSubscribed = computed(() =>
  props.user.days_subscribed != null ? props.user.days_subscribed : '-',
)
</script>

<template>
  <div class="card">
    <!-- Centered profile section -->
    <div class="flex flex-col items-center text-center">
      <!-- Large avatar -->
      <div
        v-if="user.photo_url"
        class="w-16 h-16 rounded-full bg-tg-hint/20 overflow-hidden shrink-0"
      >
        <img
          :src="user.photo_url"
          :alt="user.first_name"
          class="w-full h-full object-cover"
        >
      </div>
      <div
        v-else
        class="w-16 h-16 rounded-full bg-gradient-to-br flex items-center justify-center shrink-0"
        :class="gradientClass"
      >
        <span class="text-xl font-bold text-white">
          {{ initials }}
        </span>
      </div>

      <!-- Name -->
      <p class="mt-3 text-base font-semibold text-tg-text">
        {{ [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Без имени' }}
      </p>

      <!-- Username as link -->
      <a
        v-if="user.username"
        :href="telegramLink"
        class="text-sm text-tg-link mt-0.5"
      >
        @{{ user.username }}
      </a>

      <!-- Badges row -->
      <div class="flex items-center gap-2 mt-2">
        <StatusBadge :status="paymentStatus" />
        <StatusBadge
          v-if="!user.is_blocked"
          status="active"
          label="Активен"
        />
        <StatusBadge
          v-if="user.is_blocked"
          status="inactive"
          label="Заблокирован"
        />
      </div>
    </div>

    <!-- Stats row: "124 Дней подписки | 3 Конфигов | 15.04 Истекает" -->
    <div class="mt-4 pt-4 border-t border-black/[0.06] flex items-center justify-center gap-2 text-sm text-tg-text">
      <span>
        <span class="font-semibold">{{ daysSubscribed }}</span>
        <span class="text-tg-hint ml-0.5">Дней подписки</span>
      </span>
      <span class="text-tg-hint">|</span>
      <span>
        <span class="font-semibold">{{ configsCount }}</span>
        <span class="text-tg-hint ml-0.5">Конфигов</span>
      </span>
      <span class="text-tg-hint">|</span>
      <span>
        <span class="font-semibold">{{ expiryLabel }}</span>
        <span class="text-tg-hint ml-0.5">Истекает</span>
      </span>
    </div>
  </div>
</template>
