<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const pageTitle = computed(() => route.meta?.title || 'Админ-панель')

/** Show back button on sub-pages (non-root routes) */
const showBack = computed(() => route.path !== '/' && route.path !== '/users')

function goBack() {
  router.back()
}
</script>

<template>
  <header
    class="sticky top-0 z-30 border-b border-black/[0.08]"
    style="background: rgba(255,255,255,0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);"
  >
    <div
      class="relative flex items-center justify-center px-4"
      :class="showBack ? 'h-[58px]' : 'h-[49px]'"
    >
      <!-- Back button -->
      <button
        v-if="showBack"
        class="absolute left-2 flex items-center gap-0.5 text-[24px] leading-none active:opacity-70 transition-opacity"
        style="color: #007aff;"
        @click="goBack"
      >
        <span class="font-light">&lsaquo;</span>
      </button>

      <!-- Title -->
      <h1 class="text-[17px] font-semibold truncate" style="color: #1a1a2e;">
        {{ pageTitle }}
      </h1>
    </div>
  </header>
</template>
