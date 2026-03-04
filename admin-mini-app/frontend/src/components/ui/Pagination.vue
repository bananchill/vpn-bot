<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: {
    type: Number,
    required: true,
  },
  totalPages: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits(['update:currentPage'])

/**
 * Build a window of page numbers around the current page.
 * Shows at most 5 page buttons to avoid overflow on mobile.
 */
const pages = computed(() => {
  const total = props.totalPages
  const current = props.currentPage

  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const start = Math.max(1, current - 2)
  const end = Math.min(total, start + 4)
  const adjustedStart = Math.max(1, end - 4)

  return Array.from({ length: end - adjustedStart + 1 }, (_, i) => adjustedStart + i)
})

function goTo(page) {
  if (page >= 1 && page <= props.totalPages && page !== props.currentPage) {
    emit('update:currentPage', page)
  }
}
</script>

<template>
  <div v-if="totalPages > 1" class="flex items-center justify-center gap-1 py-3">
    <!-- Previous -->
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg text-sm transition-colors"
      :class="currentPage === 1 ? 'text-tg-hint/40 cursor-not-allowed' : 'text-tg-text active:bg-tg-secondary-bg'"
      :disabled="currentPage === 1"
      @click="goTo(currentPage - 1)"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
    </button>

    <!-- Page numbers -->
    <button
      v-for="page in pages"
      :key="page"
      class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors"
      :class="page === currentPage
        ? 'bg-blue-500 text-white'
        : 'text-tg-text active:bg-tg-secondary-bg'"
      @click="goTo(page)"
    >
      {{ page }}
    </button>

    <!-- Next -->
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg text-sm transition-colors"
      :class="currentPage === totalPages ? 'text-tg-hint/40 cursor-not-allowed' : 'text-tg-text active:bg-tg-secondary-bg'"
      :disabled="currentPage === totalPages"
      @click="goTo(currentPage + 1)"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </button>
  </div>
</template>
