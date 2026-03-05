<script setup>
import { computed, ref } from 'vue'
import WebApp from '@twa-dev/sdk'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'

const props = defineProps({
  configs: {
    type: Array,
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle', 'toggle-all'])

/** Track which individual configs are mid-request to disable their switch */
const pendingIds = ref(new Set())

/**
 * Local enabled state per config (not from DB -- managed client-side).
 * Starts as all-enabled; toggling flips locally + calls panel via parent.
 */
const enabledMap = ref({})

function isEnabled(configId) {
  return enabledMap.value[configId] !== false
}

const allEnabled = computed(() =>
  props.configs.length > 0 && props.configs.every((c) => isEnabled(c.id)),
)

async function handleToggle(config) {
  if (pendingIds.value.has(config.id)) return

  const newState = !isEnabled(config.id)
  WebApp.HapticFeedback?.impactOccurred?.('light')

  // Optimistic: flip immediately
  enabledMap.value[config.id] = newState
  pendingIds.value.add(config.id)

  try {
    await new Promise((resolve, reject) => {
      emit('toggle', {
        configId: config.id,
        enabled: newState,
        resolve,
        reject,
      })
    })
  } catch {
    // Revert on failure
    enabledMap.value[config.id] = !newState
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    pendingIds.value.delete(config.id)
  }
}

const bulkPending = ref(false)

async function handleToggleAll() {
  if (bulkPending.value) return

  const newState = !allEnabled.value
  WebApp.HapticFeedback?.impactOccurred?.('medium')

  // Snapshot previous states for rollback
  const previousStates = {}
  props.configs.forEach((c) => {
    previousStates[c.id] = isEnabled(c.id)
  })

  // Optimistic: flip all immediately
  props.configs.forEach((c) => {
    enabledMap.value[c.id] = newState
  })

  bulkPending.value = true

  try {
    await new Promise((resolve, reject) => {
      emit('toggle-all', {
        enabled: newState,
        resolve,
        reject,
      })
    })
  } catch {
    // Revert all to previous states
    Object.entries(previousStates).forEach(([id, enabled]) => {
      enabledMap.value[id] = enabled
    })
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    bulkPending.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-2">
      <h3 class="text-[16px] font-semibold" style="color: #1a1a2e;">
        VPN-конфигурации
      </h3>
      <!-- Bulk toggle button -->
      <button
        v-if="configs.length > 0"
        class="text-[13px] font-medium active:opacity-70 transition-opacity"
        style="color: #007aff;"
        :disabled="disabled || bulkPending"
        @click="handleToggleAll"
      >
        {{ allEnabled ? 'Все выкл.' : 'Все вкл.' }}
      </button>
    </div>

    <!-- Empty state -->
    <p
      v-if="configs.length === 0"
      class="text-[14px] text-center py-4"
      style="color: #8e8e93;"
    >
      Нет конфигов
    </p>

    <!-- Config rows -- iOS grouped style -->
    <div
      v-else
      class="bg-white rounded-[16px] overflow-hidden"
      style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
    >
      <div
        v-for="(config, index) in configs"
        :key="config.id"
        class="flex items-center justify-between px-4 py-3"
        :class="index < configs.length - 1 ? 'border-b border-black/[0.06]' : ''"
      >
        <div class="flex-1 min-w-0">
          <p class="text-[14px] font-medium truncate" style="color: #1a1a2e;">
            {{ config.email }}
          </p>
          <p class="text-[12px] mt-0.5" style="color: #8e8e93;">
            {{ config.protocol.toUpperCase() }}
          </p>
        </div>
        <ToggleSwitch
          :model-value="isEnabled(config.id)"
          :disabled="disabled || pendingIds.has(config.id) || bulkPending"
          @update:model-value="handleToggle(config)"
        />
      </div>
    </div>
  </div>
</template>
