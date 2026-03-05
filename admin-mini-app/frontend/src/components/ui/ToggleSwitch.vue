<script setup>
import WebApp from '@twa-dev/sdk'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

function toggle() {
  if (props.disabled) return

  // Haptic feedback for physical toggle sensation
  WebApp.HapticFeedback?.impactOccurred?.('light')

  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <button
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="relative inline-flex shrink-0 cursor-pointer items-center rounded-[16px] transition-colors duration-200 focus:outline-none"
    :class="[
      disabled ? 'opacity-50 cursor-not-allowed' : '',
    ]"
    :style="{
      width: '51px',
      height: '31px',
      backgroundColor: modelValue ? '#34c759' : '#e9e9eb',
    }"
    @click="toggle"
  >
    <span
      class="inline-block rounded-[14px] bg-white transition-transform duration-200"
      :style="{
        width: '27px',
        height: '27px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
        transform: modelValue ? 'translateX(22px)' : 'translateX(2px)',
      }"
    />
  </button>
</template>
