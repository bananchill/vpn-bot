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
})

const config = computed(() => {
  const map = {
    paid: { label: 'Оплачено', classes: 'bg-green-100 text-green-700' },
    unpaid: { label: 'Не оплачено', classes: 'bg-red-100 text-red-700' },
    expired: { label: 'Истекло', classes: 'bg-orange-100 text-orange-700' },
    expiring: { label: 'Истекает', classes: 'bg-orange-100 text-orange-700' },
    active: { label: 'Активен', classes: 'bg-blue-100 text-blue-700' },
    inactive: { label: 'Неактивен', classes: 'bg-gray-100 text-gray-500' },
  }
  return map[props.status] || { label: props.status, classes: 'bg-gray-100 text-gray-500' }
})

const displayLabel = computed(() => props.label || config.value.label)
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium"
    :class="config.classes"
  >
    {{ displayLabel }}
  </span>
</template>
