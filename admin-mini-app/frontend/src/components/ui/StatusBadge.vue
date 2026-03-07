<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * Status determines the badge color and label.
   * Supported values: 'paid', 'unpaid', 'expired', 'expiring', 'active', 'inactive'
   */
  status: {
    type: String,
    required: true,
  },
  /** Override the default label */
  label: {
    type: String,
    default: '',
  },
  /** Size variant: 'sm' for list items, 'lg' for detail page */
  size: {
    type: String,
    default: 'sm',
  },
})

const config = computed(() => {
  const map = {
    paid: { label: 'Оплачено', bg: '#e8f5e9', text: '#2e7d32' },
    unpaid: { label: 'Не оплачено', bg: '#fce4ec', text: '#c62828' },
    expired: { label: 'Истекло', bg: '#fce4ec', text: '#c62828' },
    expiring: { label: 'Истекает', bg: '#fff3e0', text: '#e65100' },
    active: { label: 'Активен', bg: '#e3f2fd', text: '#1565c0' },
    inactive: { label: 'Неактивен', bg: '#fce4ec', text: '#c62828' },
  }
  return map[props.status] || { label: props.status, bg: '#f5f5f7', text: '#8e8e93' }
})

const displayLabel = computed(() => props.label || config.value.label)

const sizeClasses = computed(() => {
  if (props.size === 'lg') {
    return 'rounded-[8px] px-[12px] py-[4px] text-[12px]'
  }
  return 'rounded-[6px] px-[8px] py-[2px] text-[11px]'
})
</script>

<template>
  <span
    class="inline-flex items-center font-semibold whitespace-nowrap"
    :class="sizeClasses"
    :style="{
      backgroundColor: config.bg,
      color: config.text,
    }"
  >
    {{ displayLabel }}
  </span>
</template>
