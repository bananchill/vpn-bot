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
 * Build page items with ellipsis.
 * Returns an array of numbers and '...' strings.
 */
const pageItems = computed(() => {
  const total = props.totalPages
  const current = props.currentPage

  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const items = []

  // Always show first page
  items.push(1)

  if (current > 3) {
    items.push('...')
  }

  // Pages around current
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  for (let i = start; i <= end; i++) {
    items.push(i)
  }

  if (current < total - 2) {
    items.push('...')
  }

  // Always show last page
  if (total > 1) {
    items.push(total)
  }

  return items
})

function goTo(page) {
  if (typeof page !== 'number') return
  if (page >= 1 && page <= props.totalPages && page !== props.currentPage) {
    emit('update:currentPage', page)
  }
}
</script>

<template>
  <div v-if="totalPages > 1" class="flex items-center justify-center gap-[4px] py-3">
    <template v-for="(item, idx) in pageItems" :key="idx">
      <!-- Ellipsis -->
      <span
        v-if="item === '...'"
        class="w-[36px] h-[36px] flex items-center justify-center text-[14px] font-medium"
        style="color: #8e8e93;"
      >
        ...
      </span>

      <!-- Page number button -->
      <button
        v-else
        class="w-[36px] h-[36px] flex items-center justify-center rounded-[10px] text-[14px] font-medium transition-colors"
        :style="{
          backgroundColor: item === currentPage ? '#007aff' : '#ffffff',
          color: item === currentPage ? '#ffffff' : '#8e8e93',
          boxShadow: item !== currentPage ? '0 1px 3px rgba(0,0,0,0.04)' : 'none',
        }"
        @click="goTo(item)"
      >
        {{ item }}
      </button>
    </template>
  </div>
</template>
