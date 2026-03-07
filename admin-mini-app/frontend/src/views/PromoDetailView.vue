<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import { usePromosStore } from '@/stores/promos'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Pagination from '@/components/ui/Pagination.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'
import {
  calcProgressPercent,
  formatExpiryDate,
  checkIsExpired,
  getStatusInfo,
} from '@/components/promos/promo-helpers'

const route = useRoute()
const router = useRouter()
const store = usePromosStore()

// -- local UI state -----------------------------------------------------------

const toggleLoading = ref(false)
const deleteLoading = ref(false)
const showDeleteModal = ref(false)

// -- lifecycle ----------------------------------------------------------------

onMounted(() => {
  const id = Number(route.params.id)
  store.fetchPromo(id)
  store.fetchUsages(id)
})

// -- computed -----------------------------------------------------------------

const promo = computed(() => store.currentPromo)

const progressPercent = computed(() =>
  calcProgressPercent(promo.value?.current_activations, promo.value?.max_activations),
)

const expiryLabel = computed(() => {
  if (!promo.value?.valid_until) return '-'
  return formatExpiryDate(promo.value.valid_until) || '-'
})

const createdLabel = computed(() => {
  if (!promo.value?.created_at) return '-'
  return formatExpiryDate(promo.value.created_at) || '-'
})

const isExpired = computed(() => {
  if (!promo.value) return false
  return checkIsExpired(promo.value)
})

const statusInfo = computed(() => {
  if (!promo.value) return { label: 'Неизвестен', bg: '#f5f5f7', color: '#8e8e93' }
  return getStatusInfo(promo.value)
})

const statusKey = computed(() => {
  if (isExpired.value) return 'expired'
  if (!promo.value?.is_active) return 'inactive'
  return 'active'
})

const statusLabel = computed(() => statusInfo.value.label)

/**
 * Format valid_until as DD.MM for the stats row in the top card.
 * Example: "2026-04-04T00:00:00" → "04.04"
 */
const expiryShort = computed(() => {
  if (!promo.value?.valid_until) return '-'
  const d = new Date(promo.value.valid_until)
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  return `${day}.${month}`
})

// -- actions ------------------------------------------------------------------

async function handleToggle() {
  if (toggleLoading.value || !promo.value) return
  toggleLoading.value = true

  try {
    await store.togglePromo(promo.value.id, !promo.value.is_active)
    WebApp.HapticFeedback?.notificationOccurred?.('success')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    toggleLoading.value = false
  }
}

function requestDelete() {
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (deleteLoading.value || !promo.value) return
  deleteLoading.value = true

  try {
    await store.deletePromo(promo.value.id)
    WebApp.HapticFeedback?.notificationOccurred?.('success')
    showDeleteModal.value = false
    router.push({ name: 'promos' })
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    deleteLoading.value = false
  }
}

function handleUsagesPageChange(newPage) {
  store.fetchUsages(promo.value.id, { page: newPage })
}

// -- helpers ------------------------------------------------------------------

function formatUsageDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** CSS gradient backgrounds for user avatars */
const gradients = [
  'linear-gradient(135deg, #667eea, #764ba2)',
  'linear-gradient(135deg, #4facfe, #00f2fe)',
  'linear-gradient(135deg, #f093fb, #f5576c)',
  'linear-gradient(135deg, #43e97b, #38f9d7)',
  'linear-gradient(135deg, #fa709a, #fee140)',
]

function userGradient(userId) {
  const index = Math.abs(userId || 0) % gradients.length
  return gradients[index]
}

function userInitial(usage) {
  const name = usage.first_name || usage.username || ''
  return name.charAt(0).toUpperCase() || '?'
}

function userDisplayName(usage) {
  if (usage.username) return `@${usage.username}`
  if (usage.first_name) return usage.first_name
  return `ID: ${usage.user_id}`
}
</script>

<template>
  <div class="px-4 py-5 space-y-4">
    <!-- Loading -->
    <LoadingSpinner
      v-if="store.loadingDetail"
      message="Загрузка..."
    />

    <!-- Error -->
    <div
      v-else-if="store.detailError"
      class="card"
    >
      <p class="text-sm text-center py-4" style="color: #c62828;">
        {{ store.detailError }}
      </p>
    </div>

    <!-- Content -->
    <template v-else-if="promo">
      <!-- Top card: code + discount + status + progress + stats -->
      <div
        class="bg-white rounded-[20px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <div class="flex flex-col items-center text-center px-5 pt-5 pb-0">
          <!-- Large code -->
          <p class="text-[24px] font-bold tracking-wider" style="color: #1a1a2e;">
            {{ promo.code }}
          </p>

          <!-- Discount badge -->
          <span
            class="mt-2 rounded-[8px] px-[12px] py-[4px] text-[14px] font-semibold"
            style="background-color: #e8f5e9; color: #2e7d32;"
          >
            -{{ promo.discount_percent }}%
          </span>

          <!-- Status badge row -->
          <div class="flex justify-center gap-2 mt-3">
            <StatusBadge
              :status="statusKey"
              :label="statusLabel"
              size="lg"
            />
          </div>

          <!-- Progress bar -->
          <div class="w-full mt-4 px-2">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[13px]" style="color: #8e8e93;">
                Использований
              </span>
              <span class="text-[13px] font-medium" style="color: #1a1a2e;">
                {{ promo.current_activations }} / {{ promo.max_activations }}
              </span>
            </div>
            <div class="w-full h-[6px] rounded-[3px]" style="background-color: #f5f5f7;">
              <div
                class="h-full rounded-[3px] transition-all duration-300"
                :style="{
                  width: progressPercent + '%',
                  backgroundColor: progressPercent >= 100 ? '#c62828' : progressPercent >= 80 ? '#e65100' : '#007aff',
                }"
              />
            </div>
          </div>
        </div>

        <!-- Stats row: 3 columns -->
        <div
          class="flex border-t mt-4 pt-[17px] pb-[16px] px-[18px]"
          style="border-color: rgba(0,0,0,0.06);"
        >
          <!-- Col 1: Activations -->
          <div class="flex-1 flex flex-col items-center">
            <span class="text-[18px] font-bold" style="color: #1a1a2e;">
              {{ promo.current_activations }}
            </span>
            <span class="text-[11px] mt-0.5" style="color: #8e8e93;">
              Активаций
            </span>
          </div>

          <!-- Divider -->
          <div class="w-px h-[30px] self-center" style="background-color: rgba(0,0,0,0.06);" />

          <!-- Col 2: Discount -->
          <div class="flex-1 flex flex-col items-center">
            <span class="text-[18px] font-bold" style="color: #1a1a2e;">
              {{ promo.discount_percent }}%
            </span>
            <span class="text-[11px] mt-0.5" style="color: #8e8e93;">
              Скидка
            </span>
          </div>

          <!-- Divider -->
          <div class="w-px h-[30px] self-center" style="background-color: rgba(0,0,0,0.06);" />

          <!-- Col 3: Expiry -->
          <div class="flex-1 flex flex-col items-center">
            <span class="text-[18px] font-bold" style="color: #1a1a2e;">
              {{ expiryShort }}
            </span>
            <span class="text-[11px] mt-0.5" style="color: #8e8e93;">
              Истекает
            </span>
          </div>
        </div>
      </div>

      <!-- Info card -->
      <div>
        <p
          class="text-[13px] font-semibold uppercase tracking-[0.5px] mb-2 px-1"
          style="color: #8e8e93;"
        >
          Информация
        </p>
        <div
          class="bg-white rounded-[16px] overflow-hidden"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <!-- Status row -->
          <div
            class="flex items-center justify-between px-4 py-3 border-b"
            style="border-color: rgba(0,0,0,0.06);"
          >
            <span class="text-[15px]" style="color: #1a1a2e;">Статус</span>
            <StatusBadge
              :status="statusKey"
              :label="statusLabel"
              size="lg"
            />
          </div>

          <!-- Created row -->
          <div
            class="flex items-center justify-between px-4 py-3 border-b"
            style="border-color: rgba(0,0,0,0.06);"
          >
            <span class="text-[15px]" style="color: #1a1a2e;">Создан</span>
            <span class="text-[15px]" style="color: #8e8e93;">
              {{ createdLabel }}
            </span>
          </div>

          <!-- Valid until row -->
          <div class="flex items-center justify-between px-4 py-3">
            <span class="text-[15px]" style="color: #1a1a2e;">Действует до</span>
            <span
              class="text-[15px]"
              :style="{ color: isExpired ? '#c62828' : '#8e8e93' }"
            >
              {{ expiryLabel }}
            </span>
          </div>
        </div>
      </div>

      <!-- Usages section -->
      <div>
        <p
          class="text-[13px] font-semibold uppercase tracking-[0.5px] mb-2 px-1"
          style="color: #8e8e93;"
        >
          История применений ({{ store.usagesTotal }})
        </p>

        <LoadingSpinner
          v-if="store.loadingUsages"
          message="Загрузка..."
          size="w-6 h-6"
        />

        <div
          v-else-if="store.usages.length > 0"
          class="bg-white rounded-[16px] overflow-hidden"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <div
            v-for="(usage, idx) in store.usages"
            :key="usage.user_id + '-' + idx"
            class="flex items-center gap-3 px-4 py-3"
            :class="idx < store.usages.length - 1 ? 'border-b' : ''"
            style="border-color: rgba(0,0,0,0.06);"
          >
            <!-- User avatar -->
            <div
              class="w-[36px] h-[36px] rounded-[11px] flex items-center justify-center shrink-0"
              :style="{ background: userGradient(usage.user_id) }"
            >
              <span class="text-[14px] font-semibold text-white">
                {{ userInitial(usage) }}
              </span>
            </div>

            <!-- User info -->
            <div class="flex-1 min-w-0">
              <p class="text-[14px] font-medium truncate" style="color: #1a1a2e;">
                {{ userDisplayName(usage) }}
              </p>
              <p class="text-[12px]" style="color: #8e8e93;">
                {{ formatUsageDate(usage.used_at) }}
              </p>
            </div>
          </div>
        </div>

        <div
          v-else
          class="bg-white rounded-[16px] px-4 py-6 text-center"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <p class="text-[14px]" style="color: #8e8e93;">
            Промокод ещё никто не использовал
          </p>
        </div>

        <!-- Usages pagination -->
        <Pagination
          v-if="store.usagesPages > 1"
          :current-page="store.usagesPage"
          :total-pages="store.usagesPages"
          @update:current-page="handleUsagesPageChange"
        />
      </div>

      <!-- Action buttons -->
      <div class="space-y-2 pt-2">
        <button
          v-if="!isExpired"
          class="w-full rounded-[14px] h-[47px] text-[15px] font-semibold active:opacity-80 transition-opacity flex items-center justify-center disabled:opacity-50"
          :style="{
            backgroundColor: promo.is_active ? '#fff3e0' : '#007aff',
            color: promo.is_active ? '#e65100' : '#ffffff',
          }"
          :disabled="toggleLoading"
          @click="handleToggle"
        >
          {{
            toggleLoading
              ? 'Обновление...'
              : promo.is_active
                ? 'Деактивировать'
                : 'Активировать'
          }}
        </button>

        <button
          class="w-full rounded-[14px] h-[47px] text-[15px] font-semibold active:opacity-80 transition-opacity flex items-center justify-center"
          style="background-color: #fce4ec; color: #c62828;"
          @click="requestDelete"
        >
          Удалить
        </button>
      </div>
    </template>

    <!-- Delete confirmation modal -->
    <ConfirmModal
      :visible="showDeleteModal"
      title="Удалить промокод"
      :message="`Удалить промокод ${promo?.code || ''}? Это действие нельзя отменить.`"
      confirm-label="Удалить"
      :danger="true"
      @confirm="confirmDelete"
      @cancel="showDeleteModal = false"
    />
  </div>
</template>
