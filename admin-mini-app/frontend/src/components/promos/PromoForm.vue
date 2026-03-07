<script setup>
import { ref, computed } from 'vue'
import WebApp from '@twa-dev/sdk'

const emit = defineEmits(['submit'])

const props = defineProps({
  /** Whether the parent is currently submitting */
  submitting: {
    type: Boolean,
    default: false,
  },
  /** External function to generate a code */
  generateCodeFn: {
    type: Function,
    default: null,
  },
})

// -- form state ---------------------------------------------------------------

const code = ref('')
const discountPercent = ref('')
const maxActivations = ref('')
const validityMode = ref('preset') // 'preset' | 'custom'
const selectedPreset = ref(null) // 7, 14, 30, 90
const customDate = ref('')
const generating = ref(false)

const presets = [
  { days: 7, label: '7 д' },
  { days: 14, label: '14 д' },
  { days: 30, label: '30 д' },
  { days: 90, label: '90 д' },
]

// -- validation ---------------------------------------------------------------

const errors = ref({})

const isValid = computed(() => {
  const c = code.value.trim()
  const d = Number(discountPercent.value)
  const m = Number(maxActivations.value)

  if (!c) return false
  if (!/^[A-Za-z0-9]+$/.test(c)) return false
  if (c.length > 32) return false
  if (!d || d < 1 || d > 100) return false
  if (!m || m < 1) return false

  if (validityMode.value === 'preset' && !selectedPreset.value) return false
  if (validityMode.value === 'custom' && !customDate.value) return false

  return true
})

function validate() {
  const errs = {}
  const c = code.value.trim()
  const d = Number(discountPercent.value)
  const m = Number(maxActivations.value)

  if (!c) {
    errs.code = 'Введите код промокода'
  } else if (!/^[A-Za-z0-9]+$/.test(c)) {
    errs.code = 'Только латиница и цифры'
  } else if (c.length > 32) {
    errs.code = 'Максимум 32 символа'
  }

  if (!d || d < 1 || d > 100) {
    errs.discount = 'Укажите скидку от 1 до 100%'
  }

  if (!m || m < 1) {
    errs.maxActivations = 'Укажите лимит активаций'
  }

  if (validityMode.value === 'preset' && !selectedPreset.value) {
    errs.validity = 'Выберите срок действия'
  }

  if (validityMode.value === 'custom') {
    if (!customDate.value) {
      errs.validity = 'Укажите дату окончания'
    } else if (new Date(customDate.value) <= new Date()) {
      errs.validity = 'Дата должна быть в будущем'
    }
  }

  errors.value = errs
  return Object.keys(errs).length === 0
}

// -- actions ------------------------------------------------------------------

async function handleGenerateCode() {
  if (!props.generateCodeFn || generating.value) return
  generating.value = true

  try {
    const generatedCode = await props.generateCodeFn()
    code.value = generatedCode
    WebApp.HapticFeedback?.impactOccurred?.('light')
  } catch {
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    generating.value = false
  }
}

function selectPreset(days) {
  validityMode.value = 'preset'
  selectedPreset.value = days
  customDate.value = ''
}

function switchToCustom() {
  validityMode.value = 'custom'
  selectedPreset.value = null
}

function handleSubmit() {
  if (!validate()) return

  const payload = {
    code: code.value.trim().toUpperCase(),
    discount_percent: Number(discountPercent.value),
    max_activations: Number(maxActivations.value),
  }

  if (validityMode.value === 'preset') {
    payload.valid_days = selectedPreset.value
  } else {
    payload.valid_until = new Date(customDate.value).toISOString()
  }

  emit('submit', payload)
}
</script>

<template>
  <div class="space-y-5">
    <!-- Code field -->
    <div>
      <p
        class="text-[13px] font-semibold uppercase tracking-[0.5px] mb-2 px-1"
        style="color: #8e8e93;"
      >
        Код промокода
      </p>
      <div
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <div class="flex items-center px-4 py-3">
          <input
            v-model="code"
            type="text"
            maxlength="32"
            placeholder="SUMMER25"
            class="flex-1 min-w-0 bg-transparent border-none outline-none text-[15px] font-medium uppercase tracking-wide"
            style="color: #1a1a2e;"
          >
          <button
            v-if="generateCodeFn"
            class="shrink-0 ml-3 rounded-[10px] px-3 py-1.5 text-[13px] font-medium active:opacity-70 transition-opacity"
            style="background-color: #e3f2fd; color: #1565c0;"
            :disabled="generating"
            @click="handleGenerateCode"
          >
            {{ generating ? '...' : 'Сгенерировать' }}
          </button>
        </div>
      </div>
      <p
        v-if="errors.code"
        class="text-[12px] mt-1 px-1"
        style="color: #c62828;"
      >
        {{ errors.code }}
      </p>
    </div>

    <!-- Discount + Max activations grouped -->
    <div>
      <p
        class="text-[13px] font-semibold uppercase tracking-[0.5px] mb-2 px-1"
        style="color: #8e8e93;"
      >
        Параметры
      </p>
      <div
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <!-- Discount row -->
        <div class="flex items-center justify-between px-4 py-3 border-b" style="border-color: rgba(0,0,0,0.06);">
          <span class="text-[15px]" style="color: #1a1a2e;">Скидка</span>
          <div class="flex items-center gap-1">
            <input
              v-model="discountPercent"
              type="number"
              min="1"
              max="100"
              placeholder="25"
              class="w-[60px] bg-transparent border-none outline-none text-[15px] font-medium text-right"
              style="color: #1a1a2e;"
            >
            <span class="text-[15px]" style="color: #8e8e93;">%</span>
          </div>
        </div>
        <!-- Max activations row -->
        <div class="flex items-center justify-between px-4 py-3">
          <span class="text-[15px]" style="color: #1a1a2e;">Макс. активаций</span>
          <input
            v-model="maxActivations"
            type="number"
            min="1"
            placeholder="100"
            class="w-[80px] bg-transparent border-none outline-none text-[15px] font-medium text-right"
            style="color: #1a1a2e;"
          >
        </div>
      </div>
      <p
        v-if="errors.discount || errors.maxActivations"
        class="text-[12px] mt-1 px-1"
        style="color: #c62828;"
      >
        {{ errors.discount || errors.maxActivations }}
      </p>
    </div>

    <!-- Validity period -->
    <div>
      <p
        class="text-[13px] font-semibold uppercase tracking-[0.5px] mb-2 px-1"
        style="color: #8e8e93;"
      >
        Срок действия
      </p>

      <!-- Preset chips -->
      <div class="flex gap-2 mb-3">
        <button
          v-for="preset in presets"
          :key="preset.days"
          class="rounded-[20px] h-[34px] px-[16px] text-[13px] font-medium transition-colors flex items-center"
          :style="{
            backgroundColor: validityMode === 'preset' && selectedPreset === preset.days ? '#007aff' : '#ffffff',
            color: validityMode === 'preset' && selectedPreset === preset.days ? '#ffffff' : '#8e8e93',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
          }"
          @click="selectPreset(preset.days)"
        >
          {{ preset.label }}
        </button>
        <button
          class="rounded-[20px] h-[34px] px-[16px] text-[13px] font-medium transition-colors flex items-center"
          :style="{
            backgroundColor: validityMode === 'custom' ? '#007aff' : '#ffffff',
            color: validityMode === 'custom' ? '#ffffff' : '#8e8e93',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
          }"
          @click="switchToCustom"
        >
          Дата
        </button>
      </div>

      <!-- Custom date input -->
      <div
        v-if="validityMode === 'custom'"
        class="bg-white rounded-[16px] overflow-hidden"
        style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
      >
        <div class="flex items-center px-4 py-3">
          <span class="text-[15px] flex-1" style="color: #1a1a2e;">Действует до</span>
          <input
            v-model="customDate"
            type="date"
            class="bg-transparent border-none outline-none text-[15px] font-medium"
            style="color: #007aff;"
          >
        </div>
      </div>

      <p
        v-if="errors.validity"
        class="text-[12px] mt-1 px-1"
        style="color: #c62828;"
      >
        {{ errors.validity }}
      </p>
    </div>

    <!-- Submit button -->
    <button
      class="btn-primary"
      :disabled="submitting || !isValid"
      @click="handleSubmit"
    >
      {{ submitting ? 'Создание...' : 'Создать промокод' }}
    </button>
  </div>
</template>

<style scoped>
/* Remove number input arrows */
input[type='number']::-webkit-outer-spin-button,
input[type='number']::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
input[type='number'] {
  -moz-appearance: textfield;
}

input::placeholder {
  color: #c7c7cc;
}
</style>
