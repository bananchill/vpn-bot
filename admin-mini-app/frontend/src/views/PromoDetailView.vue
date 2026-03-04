<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="px-4 py-5">
    <div class="card">
      <p class="text-sm text-tg-hint text-center py-6">
        Промокод #{{ route.params.id }}
      </p>
    </div>
  </div>
</template>
