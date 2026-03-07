<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import {
  calcProgressPercent,
  formatExpiryDate,
  checkIsExpired,
  getStatusInfo,
} from './promo-helpers'

const props = defineProps({
  promo: {
    type: Object,
    required: true,
  },
})

const router = useRouter()

const progressPercent = computed(() =>
  calcProgressPercent(props.promo.current_activations, props.promo.max_activations),
)

const expiryLabel = computed(() => formatExpiryDate(props.promo.valid_until) || null)

const isExpired = computed(() => checkIsExpired(props.promo))

const statusInfo = computed(() => getStatusInfo(props.promo))
const statusLabel = computed(() => statusInfo.value.label)
const statusStyle = computed(() => ({ bg: statusInfo.value.bg, color: statusInfo.value.color }))

const isInactive = computed(() => !props.promo.is_active || isExpired.value)

function navigateToDetail() {
  WebApp.HapticFeedback?.impactOccurred?.('light')
  router.push({ name: 'promo-detail', params: { id: props.promo.id } })
}
</script>

<template>
  <button
    class="w-full bg-white rounded-[16px] p-[16px] text-left active:opacity-80 transition-opacity"
    style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
    :style="{ opacity: isInactive ? 0.6 : 1 }"
    @click="navigateToDetail"
  >
    <!-- Top row: code + discount badge -->
    <div class="flex items-center justify-between">
      <span
        class="text-[17px] font-bold tracking-wide"
        style="color: #1a1a2e;"
      >
        {{ promo.code }}
      </span>
      <span
        class="rounded-[8px] px-[10px] py-[3px] text-[13px] font-semibold"
        style="background-color: #e8f5e9; color: #2e7d32;"
      >
        -{{ promo.discount_percent }}%
      </span>
    </div>

    <!-- Progress bar -->
    <div class="mt-3">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-[12px]" style="color: #8e8e93;">
          Активаций: {{ promo.current_activations }}/{{ promo.max_activations }}
        </span>
        <span class="text-[12px] font-medium" style="color: #8e8e93;">
          {{ progressPercent }}%
        </span>
      </div>
      <div class="w-full h-[6px] rounded-full" style="background-color: #f0f0f0;">
        <div
          class="h-full rounded-full transition-all duration-300"
          :style="{
            width: progressPercent + '%',
            backgroundColor: progressPercent >= 90 ? '#e65100' : '#007aff',
          }"
        />
      </div>
    </div>

    <!-- Bottom row: status + expiry -->
    <div class="flex items-center justify-between mt-3">
      <span
        class="rounded-[6px] px-[8px] py-[2px] text-[11px] font-semibold"
        :style="{
          backgroundColor: statusStyle.bg,
          color: statusStyle.color,
        }"
      >
        {{ statusLabel }}
      </span>
      <span
        v-if="expiryLabel"
        class="text-[12px]"
        style="color: #8e8e93;"
      >
        до {{ expiryLabel }}
      </span>
    </div>
  </button>
</template>
