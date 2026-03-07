<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { name: 'dashboard', path: '/', label: 'Главная', emoji: '\uD83C\uDFE0' },
  { name: 'users', path: '/users', label: 'Юзеры', emoji: '\uD83D\uDC65' },
  { name: 'promos', path: '/promos', label: 'Промо', emoji: '\uD83C\uDFF7\uFE0F' },
  { name: 'more', path: '/logs', label: 'Ещё', emoji: '\u2022\u2022\u2022' },
]

const activeTab = computed(() => {
  const path = route.path
  if (path === '/') return 'dashboard'
  if (path.startsWith('/users')) return 'users'
  if (path.startsWith('/promos')) return 'promos'
  // logs, admins, settings all fall under "more"
  return 'more'
})

function navigate(tab) {
  router.push(tab.path)
}
</script>

<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-40 border-t border-black/[0.08]"
    style="background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);"
  >
    <div class="flex items-center justify-around pt-[9px] pb-0 px-2" style="height: 81px;">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="flex flex-col items-center justify-start flex-1 gap-0.5 transition-colors pt-1"
        :style="{ color: activeTab === tab.name ? '#007aff' : '#8e8e93' }"
        @click="navigate(tab)"
      >
        <span class="text-[22px] leading-none">{{ tab.emoji }}</span>
        <span class="text-[10px] leading-tight">{{ tab.label }}</span>
      </button>
    </div>

    <!-- Safe area spacer for devices with home indicator -->
    <div class="h-[env(safe-area-inset-bottom)]" />
  </nav>
</template>
