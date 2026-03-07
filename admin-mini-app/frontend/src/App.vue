<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AppHeader from '@/components/ui/AppHeader.vue'
import AppNavbar from '@/components/ui/AppNavbar.vue'

const authStore = useAuthStore()

onMounted(() => {
  authStore.initialize()
})
</script>

<template>
  <div class="flex flex-col min-h-screen bg-tg-secondary-bg text-tg-text">
    <AppHeader />

    <main class="flex-1 overflow-y-auto pb-navbar">
      <router-view />
    </main>

    <AppNavbar />
  </div>
</template>
