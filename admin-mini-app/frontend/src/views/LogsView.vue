<script setup>
import { onMounted, computed } from 'vue'
import { useLogsStore } from '@/stores/logs'
import LogEntry from '@/components/logs/LogEntry.vue'
import Pagination from '@/components/ui/Pagination.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const store = useLogsStore()

/**
 * Human-readable labels for action filter chips.
 */
const actionLabels = {
  block_user: 'Блокировка',
  unblock_user: 'Разблокировка',
  extend_subscription: 'Продление',
  update_note: 'Заметка',
  toggle_config: 'Конфиг',
  toggle_all_configs: 'Все конфиги',
  update_settings: 'Настройки',
  create_promo: 'Создание промо',
  toggle_promo: 'Промо вкл/выкл',
  delete_promo: 'Удаление промо',
}

const filterOptions = computed(() => {
  return store.availableActions.map((action) => ({
    value: action,
    label: actionLabels[action] || action,
  }))
})

onMounted(() => {
  store.fetchLogs()
})

function handlePageChange(newPage) {
  store.goToPage(newPage)
}
</script>

<template>
  <div class="px-4 py-5 space-y-4">
    <!-- Filter chips -->
    <div class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
      <!-- "All" chip -->
      <button
        class="shrink-0 rounded-[20px] h-[29px] px-[14px] text-[13px] font-medium flex items-center transition-colors"
        :style="{
          backgroundColor: store.actionFilter === null ? '#007aff' : '#ffffff',
          color: store.actionFilter === null ? '#ffffff' : '#8e8e93',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }"
        @click="store.setActionFilter(null)"
      >
        Все действия
      </button>

      <!-- Dynamic action chips -->
      <button
        v-for="option in filterOptions"
        :key="option.value"
        class="shrink-0 rounded-[20px] h-[29px] px-[14px] text-[13px] font-medium flex items-center transition-colors"
        :style="{
          backgroundColor: store.actionFilter === option.value ? '#007aff' : '#ffffff',
          color: store.actionFilter === option.value ? '#ffffff' : '#8e8e93',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }"
        @click="store.setActionFilter(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <!-- Count -->
    <p
      v-if="!store.loading && store.items.length > 0"
      class="text-[13px]"
      style="color: #8e8e93;"
    >
      Найдено: {{ store.total.toLocaleString() }} записей
    </p>

    <!-- Loading -->
    <LoadingSpinner
      v-if="store.loading"
      message="Загрузка логов..."
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
        @click="store.fetchLogs()"
      >
        Повторить
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="store.items.length === 0"
      message="Нет записей"
      :description="
        store.actionFilter
          ? 'Нет логов по выбранному фильтру'
          : 'Журнал действий пуст'
      "
    />

    <!-- Logs list -->
    <template v-else>
      <div
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <div
          v-for="(log, idx) in store.items"
          :key="log.id"
          :class="idx < store.items.length - 1 ? 'border-b' : ''"
          style="border-color: rgba(0,0,0,0.06);"
        >
          <LogEntry :log="log" />
        </div>
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
