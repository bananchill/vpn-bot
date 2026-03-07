<script setup>
import { onMounted } from 'vue'
import { useUsersStore } from '@/stores/users'
import SearchInput from '@/components/ui/SearchInput.vue'
import UserCard from '@/components/users/UserCard.vue'
import Pagination from '@/components/ui/Pagination.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const store = useUsersStore()

onMounted(() => {
  // Only fetch if we have no cached data (preserves state across navigation)
  if (store.users.length === 0) {
    store.fetchUsers()
  }
})

function handleSearch(term) {
  store.setSearch(term)
}

function handlePageChange(newPage) {
  store.goToPage(newPage)
}

const filterPresets = [
  { key: 'all', label: 'Все' },
  { key: 'paid', label: 'Оплачено' },
  { key: 'unpaid', label: 'Не оплачено' },
  { key: 'expiring', label: 'Истекает' },
]
</script>

<template>
  <div class="px-4 py-5 space-y-4">
    <!-- Search -->
    <SearchInput
      :model-value="store.filters.search"
      placeholder="Поиск по имени, username или ID..."
      @update:model-value="handleSearch"
    />

    <!-- Filter chips -->
    <div class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
      <button
        v-for="preset in filterPresets"
        :key="preset.key"
        class="shrink-0 rounded-[20px] h-[29px] px-[14px] py-[7px] text-[13px] font-medium transition-colors flex items-center"
        :style="{
          backgroundColor: store.activeFilterLabel === preset.key ? '#007aff' : '#ffffff',
          color: store.activeFilterLabel === preset.key ? '#ffffff' : '#8e8e93',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }"
        @click="store.setFilter(preset.key)"
      >
        {{ preset.label }}
      </button>
    </div>

    <!-- Count text below filters -->
    <p
      v-if="!store.loading && store.users.length > 0"
      class="text-[13px]"
      style="color: #8e8e93;"
    >
      Найдено: {{ store.total.toLocaleString() }} пользователей
    </p>

    <!-- Loading -->
    <LoadingSpinner
      v-if="store.loading"
      message="Загрузка пользователей..."
    />

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="card"
    >
      <p class="text-sm text-red-500 text-center py-4">
        {{ store.error }}
      </p>
      <button
        class="btn-secondary w-full mt-2"
        @click="store.fetchUsers()"
      >
        Повторить
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="store.users.length === 0"
      message="Нет пользователей"
      :description="
        store.filters.search
          ? 'Попробуйте изменить параметры поиска'
          : 'Пользователи появятся после первых подключений к боту'
      "
    />

    <!-- Users list -->
    <template v-else>
      <div class="flex flex-col gap-[10px]">
        <UserCard
          v-for="user in store.users"
          :key="user.id"
          :user="user"
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
