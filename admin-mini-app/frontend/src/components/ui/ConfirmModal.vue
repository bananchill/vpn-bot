<script setup>
defineProps({
  /** Whether the modal is visible */
  visible: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    default: 'Подтверждение',
  },
  message: {
    type: String,
    default: 'Вы уверены?',
  },
  confirmLabel: {
    type: String,
    default: 'Подтвердить',
  },
  cancelLabel: {
    type: String,
    default: 'Отмена',
  },
  /** Apply danger styling to the confirm button */
  danger: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/40"
          @click="$emit('cancel')"
        />

        <!-- Modal panel -->
        <div class="relative w-full max-w-sm mx-4 mb-6 bg-white rounded-2xl overflow-hidden shadow-xl">
          <div class="px-5 pt-5 pb-4">
            <h3 class="text-base font-semibold text-tg-text">
              {{ title }}
            </h3>
            <p class="mt-2 text-sm text-tg-hint leading-relaxed">
              {{ message }}
            </p>
          </div>

          <div class="flex gap-3 px-5 pb-5">
            <button
              class="btn-secondary flex-1"
              @click="$emit('cancel')"
            >
              {{ cancelLabel }}
            </button>
            <button
              :class="danger ? 'btn-danger' : 'btn-primary'"
              class="flex-1"
              @click="$emit('confirm')"
            >
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
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
