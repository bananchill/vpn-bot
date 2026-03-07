<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import { usePromosStore } from '@/stores/promos'
import PromoCard from '@/components/promos/PromoCard.vue'
import Pagination from '@/components/ui/Pagination.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const store = usePromosStore()

const activeFilter = ref('all') // 'all' | 'active' | 'inactive'

const filterPresets = [
  { key: 'all', label: 'Все' },
  { key: 'active', label: 'Активные' },
  { key: 'inactive', label: 'Неактивные' },
]

onMounted(() => {
  if (store.promos.length === 0) {
    store.fetchPromos()
  }
})

function setFilter(preset) {
  activeFilter.value = preset
  store.page = 1

  const params = {}
  if (preset === 'active') params.is_active = true
  if (preset === 'inactive') params.is_active = false

  store.fetchPromos(params)
}

function handlePageChange(newPage) {
  const params = { page: newPage }
  if (activeFilter.value === 'active') params.is_active = true
  if (activeFilter.value === 'inactive') params.is_active = false

  store.fetchPromos(params)
}

function navigateToCreate() {
  WebApp.HapticFeedback?.impactOccurred?.('light')
  router.push({ name: 'promo-create' })
}
</script>

<template>
  <div class="px-4 py-5 space-y-4">
    <!-- Header + create button -->
    <div class="flex items-center justify-between">
      <h1 class="text-[22px] font-bold" style="color: #1a1a2e;">
        Промокоды
      </h1>
      <button
        class="text-[13px] font-medium active:opacity-70 transition-opacity bg-transparent border-none p-0"
        style="color: #007aff;"
        @click="navigateToCreate"
      >
        + Создать
      </button>
    </div>

    <!-- Filter chips -->
    <div class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
      <button
        v-for="preset in filterPresets"
        :key="preset.key"
        class="shrink-0 rounded-[20px] h-[29px] px-[14px] py-[7px] text-[13px] font-medium transition-colors flex items-center"
        :style="{
          backgroundColor: activeFilter === preset.key ? '#007aff' : '#ffffff',
          color: activeFilter === preset.key ? '#ffffff' : '#8e8e93',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }"
        @click="setFilter(preset.key)"
      >
        {{ preset.label }}
      </button>
    </div>

    <!-- Count -->
    <p
      v-if="!store.loading && store.promos.length > 0"
      class="text-[13px]"
      style="color: #8e8e93;"
    >
      {{ store.total.toLocaleString() }} промокода
    </p>

    <!-- Loading -->
    <LoadingSpinner
      v-if="store.loading"
      message="Загрузка промокодов..."
    />

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="card"
    >
      <p class="text-sm text-center py-4" style="color: #c62828;">
        {{ store.error }}
      </p>
      <button
        class="btn-secondary w-full mt-2"
        @click="store.fetchPromos()"
      >
        Повторить
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="store.promos.length === 0"
      message="Нет промокодов"
      :description="
        activeFilter !== 'all'
          ? 'Нет промокодов по выбранному фильтру'
          : 'Создайте первый промокод для ваших пользователей'
      "
      action-label="Создать промокод"
      @action="navigateToCreate"
    />

    <!-- Promos list -->
    <template v-else>
      <div class="flex flex-col gap-[10px]">
        <PromoCard
          v-for="promo in store.promos"
          :key="promo.id"
          :promo="promo"
        />
      </div>

      <!-- Pagination -->
      <Pagination
        :current-page="store.page"
        :total-pages="store.pages"
        @update:current-page="handlePageChange"
      />
    </template>
  </div>
</template>
