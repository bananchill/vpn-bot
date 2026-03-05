<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  user: {
    type: Object,
    required: true,
  },
})

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
  <div
    class="bg-white rounded-[20px] overflow-hidden"
    style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
  >
    <!-- Centered profile section -->
    <div class="flex flex-col items-center text-center px-4 pt-5 pb-0">
      <!-- Large avatar -->
      <div
        v-if="user.photo_url"
        class="w-[72px] h-[72px] rounded-[22px] overflow-hidden shrink-0"
      >
        <img
          :src="user.photo_url"
          :alt="user.first_name"
          class="w-full h-full object-cover"
        >
      </div>
      <div
        v-else
        class="w-[72px] h-[72px] rounded-[22px] flex items-center justify-center shrink-0"
        :style="{ background: gradientStyle }"
      >
        <span class="text-[28px] font-bold text-white">
          {{ initials }}
        </span>
      </div>

      <!-- Name -->
      <p class="mt-3 text-[20px] font-bold" style="color: #1a1a2e;">
        {{ [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Без имени' }}
      </p>

      <!-- Username as link -->
      <a
        v-if="user.username"
        :href="telegramLink"
        class="text-[14px] mt-0.5"
        style="color: #007aff;"
      >
        @{{ user.username }}
      </a>

      <!-- Badges row -->
      <div class="flex items-center gap-2 mt-2">
        <StatusBadge :status="paymentStatus" size="lg" />
        <StatusBadge
          v-if="!user.is_blocked"
          status="active"
          label="Активен"
          size="lg"
        />
        <StatusBadge
          v-if="user.is_blocked"
          status="inactive"
          label="Заблокирован"
          size="lg"
        />
      </div>
    </div>

    <!-- Stats row -->
    <div
      class="flex items-center justify-between pt-[17px] pb-4 px-[18px] mt-4 border-t border-black/[0.06]"
    >
      <div class="flex flex-col items-center flex-1">
        <span class="text-[18px] font-bold" style="color: #1a1a2e;">{{ daysSubscribed }}</span>
        <span class="text-[11px]" style="color: #8e8e93;">Дней подписки</span>
      </div>
      <div class="flex flex-col items-center flex-1">
        <span class="text-[18px] font-bold" style="color: #1a1a2e;">{{ configsCount }}</span>
        <span class="text-[11px]" style="color: #8e8e93;">Конфигов</span>
      </div>
      <div class="flex flex-col items-center flex-1">
        <span class="text-[18px] font-bold" style="color: #1a1a2e;">{{ expiryLabel }}</span>
        <span class="text-[11px]" style="color: #8e8e93;">Истекает</span>
      </div>
    </div>
  </div>
</template>
