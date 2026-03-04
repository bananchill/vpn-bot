<script setup>
defineProps({
  /** Displayed below the spinner */
  message: {
    type: String,
    default: '',
  },
  /** Spinner diameter class (e.g. "w-8 h-8") */
  size: {
    type: String,
    default: 'w-8 h-8',
  },
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-12">
    <svg
      :class="size"
      class="animate-spin text-tg-button"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
    <p v-if="message" class="text-sm text-tg-hint">
      {{ message }}
    </p>
  </div>
</template>
