<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { name: 'dashboard', path: '/', label: 'Главная', icon: 'home' },
  { name: 'users', path: '/users', label: 'Юзеры', icon: 'users' },
  { name: 'promos', path: '/promos', label: 'Промо', icon: 'tag' },
  { name: 'more', path: '/logs', label: 'Ещё', icon: 'more' },
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
  <nav class="fixed bottom-0 left-0 right-0 z-40 backdrop-blur-xl bg-white/92 border-t border-black/[0.08]">
    <div class="flex items-center justify-around h-16 px-2">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="flex flex-col items-center justify-center flex-1 h-full gap-0.5 transition-colors"
        :class="activeTab === tab.name ? 'text-tg-button' : 'text-tg-hint'"
        @click="navigate(tab)"
      >
        <!-- Home icon - filled when active -->
        <template v-if="tab.icon === 'home'">
          <svg v-if="activeTab === tab.name" class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path d="M11.47 3.841a.75.75 0 011.06 0l8.69 8.69a.75.75 0 01-.53 1.28h-1.44v7.44a.75.75 0 01-.75.75h-4.5a.75.75 0 01-.75-.75v-4.5h-2.25v4.5a.75.75 0 01-.75.75h-4.5a.75.75 0 01-.75-.75v-7.44H3.31a.75.75 0 01-.53-1.28l8.69-8.69z" />
          </svg>
          <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z" />
          </svg>
        </template>

        <!-- Users icon - filled when active -->
        <template v-else-if="tab.icon === 'users'">
          <svg v-if="activeTab === tab.name" class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8.25 6.75a3.75 3.75 0 117.5 0 3.75 3.75 0 01-7.5 0zM15.75 9.75a3 3 0 116 0 3 3 0 01-6 0zM2.25 9.75a3 3 0 116 0 3 3 0 01-6 0zM6.31 15.117A6.745 6.745 0 0112 12a6.745 6.745 0 016.709 7.498.75.75 0 01-.372.568A12.696 12.696 0 0112 21.75c-2.305 0-4.47-.612-6.337-1.684a.75.75 0 01-.372-.568 6.787 6.787 0 011.019-4.38z" />
            <path d="M5.082 14.254a8.287 8.287 0 00-1.308 5.135.75.75 0 01-1.14.554A5.58 5.58 0 011.5 15.75a5.25 5.25 0 013.582-1.496zM19.918 14.254a8.287 8.287 0 011.308 5.135.75.75 0 001.14.554A5.58 5.58 0 0022.5 15.75a5.25 5.25 0 00-3.582-1.496z" />
          </svg>
          <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </template>

        <!-- Tag icon - filled when active -->
        <template v-else-if="tab.icon === 'tag'">
          <svg v-if="activeTab === tab.name" class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path fill-rule="evenodd" d="M5.25 2.25a3 3 0 00-3 3v4.318a3 3 0 00.879 2.121l9.58 9.581c.92.92 2.39.92 3.31 0l4.318-4.318a2.25 2.25 0 000-3.31l-9.58-9.581A3 3 0 008.568 2.25H5.25zM6.75 6a.75.75 0 100 1.5.75.75 0 000-1.5z" clip-rule="evenodd" />
          </svg>
          <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" />
          </svg>
        </template>

        <!-- More (ellipsis) icon - filled when active -->
        <template v-else-if="tab.icon === 'more'">
          <svg v-if="activeTab === tab.name" class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path fill-rule="evenodd" d="M4.5 12a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zm6 0a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zm6 0a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0z" clip-rule="evenodd" />
          </svg>
          <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
          </svg>
        </template>

        <span class="text-[10px] leading-tight">{{ tab.label }}</span>
      </button>
    </div>

    <!-- Safe area spacer for devices with home indicator -->
    <div class="h-[env(safe-area-inset-bottom)]" />
  </nav>
</template>
