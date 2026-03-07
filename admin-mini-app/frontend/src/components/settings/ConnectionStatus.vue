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
  <div class="flex items-center gap-[12px]">
    <!-- Status icon -->
    <div
      class="w-[44px] h-[44px] rounded-[14px] flex items-center justify-center shrink-0 text-[22px]"
      :style="{
        backgroundColor: checking ? '#fff3e0' : checked && success ? '#e8f5e9' : checked && !success ? '#fce4ec' : '#f5f5f7',
      }"
    >
      <span v-if="checking" class="animate-pulse">&#x23F3;</span>
      <span v-else-if="checked && success">&#x2705;</span>
      <span v-else-if="checked && !success">&#x274C;</span>
      <span v-else>&#x2753;</span>
    </div>

    <!-- Status text -->
    <div class="flex flex-col min-w-0">
      <span
        v-if="checking"
        class="text-[15px] font-semibold"
        style="color: #8e8e93;"
      >
        Проверка...
      </span>

      <template v-else-if="checked">
        <span
          class="text-[15px] font-semibold"
          :style="{ color: success ? '#2e7d32' : '#c62828' }"
        >
          {{ success ? 'Панель подключена' : 'Ошибка подключения' }}
        </span>
        <span v-if="success && responseTimeMs != null" class="text-[13px]" style="color: #8e8e93;">
          Время отклика: {{ responseTimeMs }}ms
        </span>
        <span
          v-if="message && !success"
          class="text-[13px] truncate"
          style="color: #8e8e93;"
        >
          {{ message }}
        </span>
      </template>

      <span
        v-else
        class="text-[15px]"
        style="color: #8e8e93;"
      >
        Не проверено
      </span>
    </div>
  </div>
</template>
