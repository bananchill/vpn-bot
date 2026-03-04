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
    class="relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 focus:outline-none"
    :class="[
      modelValue ? 'bg-[#34c759]' : 'bg-[#787880]/[0.32]',
      disabled ? 'opacity-50 cursor-not-allowed' : '',
    ]"
    @click="toggle"
  >
    <span
      class="inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200"
      :class="modelValue ? 'translate-x-6' : 'translate-x-1'"
    />
  </button>
</template>
