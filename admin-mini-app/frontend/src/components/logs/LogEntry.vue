<script setup>
import { computed } from 'vue'

const props = defineProps({
  log: {
    type: Object,
    required: true,
  },
})

/**
 * Map action types to icon emoji and background color.
 * Grouped by operation category for visual clarity.
 */
const actionConfig = computed(() => {
  const map = {
    block_user: { icon: '\uD83D\uDEAB', bg: '#fce4ec', label: 'Заблокирован' },
    unblock_user: { icon: '\u2705', bg: '#e8f5e9', label: 'Разблокирован' },
    extend_subscription: { icon: '\uD83D\uDCC5', bg: '#e3f2fd', label: 'Подписка продлена' },
    update_note: { icon: '\uD83D\uDCDD', bg: '#fff3e0', label: 'Заметка обновлена' },
    toggle_config: { icon: '\uD83D\uDD11', bg: '#f3e5f5', label: 'Конфиг' },
    toggle_all_configs: { icon: '\uD83D\uDD04', bg: '#f3e5f5', label: 'Все конфиги переключены' },
    update_settings: { icon: '\u2699\uFE0F', bg: '#f5f5f7', label: 'Настройки обновлены' },
    create_promo: { icon: '\uD83C\uDFF7\uFE0F', bg: '#e3f2fd', label: 'Создан промокод' },
    toggle_promo: { icon: '\uD83D\uDD00', bg: '#fff3e0', label: 'Промокод переключён' },
    delete_promo: { icon: '\uD83D\uDDD1\uFE0F', bg: '#fce4ec', label: 'Промокод удалён' },
  }

  return map[props.log.action] || {
    icon: '\uD83D\uDCCB',
    bg: '#f5f5f7',
    label: props.log.action,
  }
})

/**
 * Build a human-readable description that includes the target when present.
 * Examples:
 *   block_user + @ivan       → "Заблокирован @ivan"
 *   create_promo + SUMMER25  → "Создан промокод SUMMER25"
 *   update_settings          → "Настройки обновлены"
 */
const descriptionText = computed(() => {
  const label = actionConfig.value.label
  const target = props.log.target

  if (!target) return label

  // For actions where the target is a username, prepend @ if not already present
  const userActions = [
    'block_user',
    'unblock_user',
    'extend_subscription',
    'update_note',
    'toggle_config',
    'toggle_all_configs',
  ]

  if (userActions.includes(props.log.action)) {
    const display = target.startsWith('@') ? target : `@${target}`
    return `${label} ${display}`
  }

  // For promo actions the target is the promo code (no @ prefix)
  return `${label} ${target}`
})

/**
 * Format timestamp as HH:MM only (spec: "@admin -- 15:42").
 */
const formattedTime = computed(() => {
  if (!props.log.created_at) return ''
  const d = new Date(props.log.created_at)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
})

const adminLabel = computed(() => {
  if (props.log.admin_username) return `@${props.log.admin_username}`
  return `ID: ${props.log.admin_telegram_id}`
})
</script>

<template>
  <div class="flex items-center gap-3 px-4 py-3">
    <!-- Action icon -->
    <div
      class="w-[36px] h-[36px] rounded-[10px] flex items-center justify-center text-[16px] shrink-0"
      :style="{ backgroundColor: actionConfig.bg }"
    >
      {{ actionConfig.icon }}
    </div>

    <!-- Content -->
    <div class="flex-1 min-w-0">
      <p class="text-[14px] font-medium truncate" style="color: #1a1a2e;">
        {{ descriptionText }}
      </p>
      <p class="text-[12px] mt-0.5" style="color: #8e8e93;">
        {{ adminLabel }} -- {{ formattedTime }}
      </p>
    </div>
  </div>
</template>
