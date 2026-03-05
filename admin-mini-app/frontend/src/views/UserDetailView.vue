<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import { useUsersStore } from '@/stores/users'
import UserInfo from '@/components/users/UserInfo.vue'
import ConfigList from '@/components/users/ConfigList.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ConfirmModal from '@/components/ui/ConfirmModal.vue'

const route = useRoute()
const store = useUsersStore()

// -- local UI state ---------------------------------------------------------

const editingNote = ref(false)
const noteInput = ref('')
const savingNote = ref(false)

const showBlockModal = ref(false)
const blockLoading = ref(false)

const showExtendModal = ref(false)
const extendDays = ref(30)
const extendLoading = ref(false)

// -- lifecycle --------------------------------------------------------------

onMounted(() => {
  const userId = Number(route.params.id)
  store.fetchUserDetail(userId)
})

// -- note editing -----------------------------------------------------------

function startEditNote() {
  noteInput.value = store.currentUser?.admin_note || ''
  editingNote.value = true
}

function cancelEditNote() {
  editingNote.value = false
}

async function saveNote() {
  if (savingNote.value) return
  savingNote.value = true

  try {
    await store.updateNote(store.currentUser.id, noteInput.value)
    editingNote.value = false
    WebApp.HapticFeedback?.notificationOccurred?.('success')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    savingNote.value = false
  }
}

// -- block/unblock ----------------------------------------------------------

function requestBlock() {
  showBlockModal.value = true
}

async function confirmBlock() {
  if (blockLoading.value) return
  blockLoading.value = true

  try {
    const newState = !store.currentUser.is_blocked
    await store.toggleBlock(store.currentUser.id, newState)
    showBlockModal.value = false
    WebApp.HapticFeedback?.notificationOccurred?.('success')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    blockLoading.value = false
  }
}

// -- extend subscription ----------------------------------------------------

function requestExtend() {
  extendDays.value = 30
  showExtendModal.value = true
}

async function confirmExtend() {
  if (extendLoading.value || extendDays.value < 1) return
  extendLoading.value = true

  try {
    await store.extendSubscription(store.currentUser.id, extendDays.value)
    showExtendModal.value = false
    WebApp.HapticFeedback?.notificationOccurred?.('success')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    extendLoading.value = false
  }
}

// -- config toggles (called by ConfigList via promise-based events) ---------

async function handleConfigToggle({ configId, enabled, resolve, reject }) {
  try {
    await store.toggleConfig(configId, enabled)
    resolve()
  } catch (err) {
    reject(err)
  }
}

async function handleToggleAll({ enabled, resolve, reject }) {
  try {
    await store.toggleAllConfigs(store.currentUser.id, enabled)
    resolve()
  } catch (err) {
    reject(err)
  }
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
      <p class="text-sm text-red-500 text-center py-4">
        {{ store.detailError }}
      </p>
    </div>

    <!-- Content -->
    <template v-else-if="store.currentUser">
      <!-- User info block -->
      <UserInfo :user="store.currentUser" />

      <!-- Admin note -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-[16px] font-semibold" style="color: #1a1a2e;">
            Заметка администратора
          </h3>
          <button
            v-if="!editingNote"
            class="text-[13px] font-medium active:opacity-70 transition-opacity"
            style="color: #007aff;"
            @click="startEditNote"
          >
            Изменить
          </button>
        </div>

        <!-- Display mode -->
        <div
          v-if="!editingNote"
          class="bg-white rounded-[16px] px-4 py-3"
          style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
        >
          <p class="text-[14px] leading-[21px]" style="color: #3c3c43;">
            {{ store.currentUser.admin_note || 'Нет заметки' }}
          </p>
        </div>

        <!-- Edit mode -->
        <div v-else class="space-y-3">
          <textarea
            v-model="noteInput"
            class="w-full bg-white rounded-[16px] px-4 py-3 text-[14px] leading-[21px] min-h-[80px] resize-none border-none outline-none"
            style="color: #3c3c43; box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
            placeholder="Введите заметку..."
          />
          <div class="flex gap-2">
            <button
              class="btn-secondary flex-1 text-xs"
              :disabled="savingNote"
              @click="cancelEditNote"
            >
              Отмена
            </button>
            <button
              class="btn-primary flex-1 text-xs !py-2.5"
              :disabled="savingNote"
              @click="saveNote"
            >
              {{ savingNote ? 'Сохранение...' : 'Сохранить' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Config list -->
      <ConfigList
        :configs="store.currentUser.configs"
        @toggle="handleConfigToggle"
        @toggle-all="handleToggleAll"
      />

      <!-- Action buttons -->
      <div class="space-y-2 pt-2">
        <button
          v-if="!store.currentUser.is_blocked"
          class="w-full rounded-[14px] h-[47px] text-[15px] font-semibold text-white active:opacity-80 transition-opacity flex items-center justify-center"
          style="background-color: #007aff;"
          @click="requestExtend"
        >
          Продлить подписку
        </button>

        <button
          class="w-full rounded-[14px] h-[47px] text-[15px] font-semibold active:opacity-80 transition-opacity flex items-center justify-center"
          :style="{
            backgroundColor: store.currentUser.is_blocked ? '#007aff' : '#fce4ec',
            color: store.currentUser.is_blocked ? '#ffffff' : '#c62828',
          }"
          @click="requestBlock"
        >
          {{ store.currentUser.is_blocked ? 'Разблокировать' : 'Заблокировать' }}
        </button>
      </div>
    </template>

    <!-- Block confirmation modal -->
    <ConfirmModal
      :visible="showBlockModal"
      :title="store.currentUser?.is_blocked ? 'Разблокировать' : 'Заблокировать'"
      :message="
        store.currentUser?.is_blocked
          ? 'Пользователь снова сможет пользоваться сервисом.'
          : 'Пользователь будет заблокирован и не сможет пользоваться сервисом.'
      "
      :confirm-label="
        store.currentUser?.is_blocked ? 'Разблокировать' : 'Заблокировать'
      "
      :danger="!store.currentUser?.is_blocked"
      @confirm="confirmBlock"
      @cancel="showBlockModal = false"
    />

    <!-- Extend subscription modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showExtendModal"
          class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
        >
          <!-- Backdrop -->
          <div
            class="absolute inset-0 bg-black/40"
            @click="showExtendModal = false"
          />

          <!-- Modal panel -->
          <div class="relative w-full max-w-sm mx-4 mb-6 bg-white rounded-[20px] overflow-hidden" style="box-shadow: 0 8px 32px rgba(0,0,0,0.12);">
            <div class="px-5 pt-5 pb-4">
              <h3 class="text-[17px] font-semibold" style="color: #1a1a2e;">
                Продлить подписку
              </h3>
              <p class="mt-2 text-[14px]" style="color: #8e8e93;">
                Укажите количество дней для продления.
              </p>
              <input
                v-model.number="extendDays"
                type="number"
                min="1"
                max="365"
                class="w-full mt-3 bg-white rounded-[12px] px-4 py-3 text-[15px] border border-black/[0.06] outline-none"
                style="color: #1a1a2e;"
                placeholder="Количество дней"
              >
            </div>

            <div class="flex gap-3 px-5 pb-5">
              <button
                class="btn-secondary flex-1"
                @click="showExtendModal = false"
              >
                Отмена
              </button>
              <button
                class="flex-1 rounded-[14px] py-3 text-[15px] font-semibold text-white active:opacity-80 transition-opacity disabled:opacity-50"
                style="background-color: #007aff;"
                :disabled="extendLoading || extendDays < 1"
                @click="confirmExtend"
              >
                {{ extendLoading ? 'Продление...' : 'Продлить' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
