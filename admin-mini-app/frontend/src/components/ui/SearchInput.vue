<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'Поиск...',
  },
  /** Debounce delay in milliseconds */
  debounce: {
    type: Number,
    default: 300,
  },
})

const emit = defineEmits(['update:modelValue'])

const localValue = ref(props.modelValue)
let debounceTimer = null

watch(() => props.modelValue, (val) => {
  localValue.value = val
})

function onInput(event) {
  localValue.value = event.target.value

  if (debounceTimer) clearTimeout(debounceTimer)

  debounceTimer = setTimeout(() => {
    emit('update:modelValue', localValue.value)
  }, props.debounce)
}

function clear() {
  localValue.value = ''
  emit('update:modelValue', '')
}

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div
    class="flex items-center bg-white rounded-[12px] h-[41px] px-[14px] gap-[8px]"
    style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
  >
    <!-- Search emoji icon -->
    <span class="text-[16px] shrink-0 leading-none" style="color: #8e8e93;"
      >&#x1F50D;</span
    >

    <input
      type="text"
      :value="localValue"
      :placeholder="placeholder"
      class="flex-1 min-w-0 bg-transparent border-none outline-none text-[15px]"
      style="color: #1a1a2e;"
      @input="onInput"
    />

    <!-- Clear button -->
    <button
      v-if="localValue"
      class="shrink-0 w-5 h-5 flex items-center justify-center rounded-full active:opacity-70 transition-opacity"
      style="color: #8e8e93;"
      @click="clear"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
input::placeholder {
  color: #c7c7cc;
  font-size: 15px;
}
</style>
