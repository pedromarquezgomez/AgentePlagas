<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import LoginPanel from '../components/LoginPanel.vue'
import {
  AUTH_MODE,
  loginWithCredentials,
  setStoredAdminApiKey,
  type LoginPayload
} from '../services/api'

const router = useRouter()
const authMessage = ref<string | null>(null)

async function handleLogin(payload: LoginPayload): Promise<void> {
  try {
    const authIndicator = await loginWithCredentials(payload)
    if (AUTH_MODE === 'api_key' && payload.apiKey) {
      setStoredAdminApiKey(payload.apiKey)
    }
    authMessage.value = null
    // Redirigir a operaciones (o dashboard) tras autenticación exitosa
    await router.push('/operations')
  } catch (err) {
    authMessage.value = err instanceof Error ? err.message : 'No se pudo iniciar sesión'
  }
}
</script>

<template>
  <LoginPanel
    :auth-mode="AUTH_MODE"
    :message="authMessage"
    @login="handleLogin"
  />
</template>
