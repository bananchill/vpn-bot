<script setup>
defineProps({
  /** Main message shown to the user */
  message: {
    type: String,
    default: 'Нет данных',
  },
  /** Optional secondary description */
  description: {
    type: String,
    default: '',
  },
  /** Optional action button label */
  actionLabel: {
    type: String,
    default: '',
  },
})

defineEmits(['action'])
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 px-6 text-center">
    <!-- Empty box icon -->
    <svg
      class="w-16 h-16 text-tg-hint opacity-40"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="1.2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
      />
    </svg>

    <p class="text-base font-medium text-tg-text">
      {{ message }}
    </p>

    <p v-if="description" class="text-sm text-tg-hint max-w-[260px]">
      {{ description }}
    </p>

    <button
      v-if="actionLabel"
      class="btn-primary mt-2"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
