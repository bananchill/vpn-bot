<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const pageTitle = computed(() => route.meta?.title || 'Админ-панель')

/** Show back button on sub-pages (non-root routes) */
const showBack = computed(() => route.path !== '/')

function goBack() {
  router.back()
}
</script>

<template>
  <header class="sticky top-0 z-30 backdrop-blur-xl bg-tg-secondary-bg/85 border-b border-black/[0.08]">
    <div class="relative flex items-center justify-center h-12 px-4">
      <!-- Back button -->
      <button
        v-if="showBack"
        class="absolute left-2 flex items-center gap-0.5 text-tg-link text-sm font-medium active:opacity-70 transition-opacity"
        @click="goBack"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <!-- Title -->
      <h1 class="text-base font-semibold text-tg-text truncate">
        {{ pageTitle }}
      </h1>
    </div>
  </header>
</template>
