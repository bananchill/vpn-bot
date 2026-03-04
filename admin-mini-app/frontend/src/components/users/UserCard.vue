<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  user: {
    type: Object,
    required: true,
  },
})

const router = useRouter()

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

/** First letter of the name (or "?") used as avatar fallback */
const initials = computed(() => {
  const name = props.user.first_name || props.user.username || ''
  return name.charAt(0).toUpperCase() || '?'
})

/** Human-readable expiry date or a dash when not set */
const expiryLabel = computed(() => {
  if (!props.user.subscription_expires) return null
  const d = new Date(props.user.subscription_expires)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
})

const paymentStatus = computed(() =>
  props.user.is_paid ? 'paid' : 'unpaid',
)

function navigateToDetail() {
  WebApp.HapticFeedback?.impactOccurred?.('light')
  router.push({ name: 'user-detail', params: { id: props.user.id } })
}
</script>

<template>
  <button
    class="card w-full text-left flex items-center gap-3 active:opacity-80 transition-opacity"
    @click="navigateToDetail"
  >
    <!-- Avatar -->
    <div
      v-if="user.photo_url"
      class="w-11 h-11 rounded-full bg-tg-hint/20 overflow-hidden shrink-0"
    >
      <img
        :src="user.photo_url"
        :alt="user.first_name"
        class="w-full h-full object-cover"
      >
    </div>
    <div
      v-else
      class="w-11 h-11 rounded-full bg-gradient-to-br flex items-center justify-center shrink-0"
      :class="gradientClass"
    >
      <span class="text-sm font-semibold text-white">
        {{ initials }}
      </span>
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-tg-text truncate">
          {{ user.first_name || 'Без имени' }}
        </span>
        <StatusBadge :status="paymentStatus" />
      </div>
      <div class="flex items-center gap-2 mt-0.5">
        <span
          v-if="user.username"
          class="text-xs text-tg-hint truncate"
        >
          @{{ user.username }}
        </span>
        <span
          v-if="expiryLabel"
          class="text-xs text-tg-hint"
        >
          до {{ expiryLabel }}
        </span>
      </div>
    </div>

    <!-- Chevron -->
    <svg
      class="w-4 h-4 text-tg-hint shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  </button>
</template>
