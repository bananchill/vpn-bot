<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import WebApp from '@twa-dev/sdk'
import { usePromosStore } from '@/stores/promos'
import PromoForm from '@/components/promos/PromoForm.vue'

const router = useRouter()
const store = usePromosStore()

const submitting = ref(false)
const error = ref(null)

async function handleSubmit(payload) {
  submitting.value = true
  error.value = null

  try {
    await store.createPromo(payload)
    WebApp.HapticFeedback?.notificationOccurred?.('success')
    router.push({ name: 'promos' })
  } catch (err) {
    error.value = err.userMessage || 'Не удалось создать промокод'
    WebApp.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    submitting.value = false
  }
}

async function handleGenerateCode() {
  return await store.generateCode()
}
</script>

<template>
  <div class="px-4 py-5 space-y-4">
    <!-- Header -->
    <h1 class="text-[22px] font-bold" style="color: #1a1a2e;">
      Новый промокод
    </h1>

    <!-- Error banner -->
    <div
      v-if="error"
      class="rounded-[12px] px-4 py-3 text-[14px]"
      style="background-color: #fce4ec; color: #c62828;"
    >
      {{ error }}
    </div>

    <!-- Form -->
    <PromoForm
      :submitting="submitting"
      :generate-code-fn="handleGenerateCode"
      @submit="handleSubmit"
    />
  </div>
</template>
