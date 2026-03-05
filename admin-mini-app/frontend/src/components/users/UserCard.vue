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

/** CSS gradient backgrounds for fallback avatars */
const gradients = [
  'linear-gradient(135deg, #667eea, #764ba2)',
  'linear-gradient(135deg, #4facfe, #00f2fe)',
  'linear-gradient(135deg, #f093fb, #f5576c)',
  'linear-gradient(135deg, #43e97b, #38f9d7)',
  'linear-gradient(135deg, #fa709a, #fee140)',
]

/** Compute a stable gradient index based on user id */
const gradientStyle = computed(() => {
  const id = props.user.id || props.user.telegram_id || 0
  const index = Math.abs(id) % gradients.length
  return gradients[index]
})

/** First letter of the name (or "?") used as avatar fallback */
const initials = computed(() => {
  const name = props.user.first_name || props.user.username || ''
  return name.charAt(0).toUpperCase() || '?'
})

/** Human-readable expiry date or null when not set */
const expiryLabel = computed(() => {
  if (!props.user.subscription_expires) return null
  const d = new Date(props.user.subscription_expires)
  const now = new Date()
  const isExpired = d < now
  const dateStr = d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
  return isExpired ? `истёк ${dateStr}` : `до ${dateStr}`
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
    class="w-full bg-white rounded-[16px] h-[72px] flex items-center gap-[12px] px-[16px] text-left active:opacity-80 transition-opacity"
    style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
    @click="navigateToDetail"
  >
    <!-- Avatar -->
    <div
      v-if="user.photo_url"
      class="w-[44px] h-[44px] rounded-[14px] overflow-hidden shrink-0"
    >
      <img
        :src="user.photo_url"
        :alt="user.first_name"
        class="w-full h-full object-cover"
      >
    </div>
    <div
      v-else
      class="w-[44px] h-[44px] rounded-[14px] flex items-center justify-center shrink-0"
      :style="{ background: gradientStyle }"
    >
      <span class="text-[18px] font-semibold text-white">
        {{ initials }}
      </span>
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="text-[15px] font-semibold truncate" style="color: #1a1a2e;">
          {{ user.first_name || 'Без имени' }}
        </span>
        <StatusBadge :status="paymentStatus" size="sm" />
      </div>
      <div class="flex items-center gap-1 mt-0.5">
        <span
          v-if="user.username"
          class="text-[13px] truncate"
          style="color: #8e8e93;"
        >
          @{{ user.username }}
        </span>
        <span
          v-if="user.username && expiryLabel"
          class="text-[13px]"
          style="color: #8e8e93;"
        >&middot;</span>
        <span
          v-if="expiryLabel"
          class="text-[13px] whitespace-nowrap"
          style="color: #8e8e93;"
        >
          {{ expiryLabel }}
        </span>
      </div>
    </div>

    <!-- Right chevron -->
    <span class="text-[18px] shrink-0" style="color: #c7c7cc;">&rsaquo;</span>
  </button>
</template>
