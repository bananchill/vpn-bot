<script setup>
defineProps({
  /** Whether a check has been performed at least once */
  checked: {
    type: Boolean,
    default: false,
  },
  /** Whether the check is currently in progress */
  checking: {
    type: Boolean,
    default: false,
  },
  /** Result of the last check */
  success: {
    type: Boolean,
    default: false,
  },
  /** Human-readable status message from the backend */
  message: {
    type: String,
    default: '',
  },
  /** Round-trip time in milliseconds, if available */
  responseTimeMs: {
    type: Number,
    default: null,
  },
})
</script>

<template>
  <div class="flex items-center gap-3 py-2">
    <!-- Status indicator dot -->
    <span
      v-if="checking"
      class="relative flex h-3 w-3 shrink-0"
    >
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-tg-button opacity-75" />
      <span class="relative inline-flex rounded-full h-3 w-3 bg-tg-button" />
    </span>

    <span
      v-else-if="checked && success"
      class="inline-flex h-3 w-3 shrink-0 rounded-full bg-[#34c759]"
    />

    <span
      v-else-if="checked && !success"
      class="inline-flex h-3 w-3 shrink-0 rounded-full bg-red-500"
    />

    <span
      v-else
      class="inline-flex h-3 w-3 shrink-0 rounded-full bg-gray-400"
    />

    <!-- Status text -->
    <div class="flex flex-col min-w-0">
      <span
        v-if="checking"
        class="text-sm text-tg-hint"
      >
        Проверка подключения...
      </span>

      <template v-else-if="checked">
        <span
          class="text-sm font-medium"
          :class="success ? 'text-[#34c759]' : 'text-red-500'"
        >
          {{ success ? 'Подключено' : 'Ошибка' }}
          <span v-if="success && responseTimeMs != null" class="font-normal text-tg-hint">
            &middot; {{ responseTimeMs }}ms
          </span>
        </span>
        <span
          v-if="message && !success"
          class="text-xs text-tg-hint truncate"
        >
          {{ message }}
        </span>
      </template>

      <span
        v-else
        class="text-sm text-tg-hint"
      >
        Не проверено
      </span>
    </div>
  </div>
</template>
