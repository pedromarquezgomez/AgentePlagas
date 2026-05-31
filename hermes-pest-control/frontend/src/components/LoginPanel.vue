<script setup lang="ts">
import { ref } from 'vue'
import type { AuthMode, LoginPayload } from '../services/api'

const props = defineProps<{
  authMode: AuthMode
  message?: string | null
}>()

const emit = defineEmits<{
  login: [payload: LoginPayload]
}>()

const apiKey = ref('')
const email = ref('')
const password = ref('')

function submitLogin(): void {
  if (props.authMode === 'firebase') {
    if (!email.value.trim() || !password.value) return
    emit('login', {
      email: email.value.trim(),
      password: password.value,
    })
    return
  }

  if (props.authMode === 'api_key') {
    const trimmedApiKey = apiKey.value.trim()
    if (!trimmedApiKey) return
    emit('login', { apiKey: trimmedApiKey })
  }
}
</script>

<template>
  <main class="loginShell">
    <section class="loginPanel" aria-label="Acceso al panel">
      <div>
        <p class="eyebrow">Hermes Pest Control</p>
        <h1>Acceso al panel</h1>
      </div>

      <p v-if="message" class="loginMessage">{{ message }}</p>

      <form class="loginForm" @submit.prevent="submitLogin">
        <label v-if="authMode === 'api_key'">
          API key
          <input
            v-model="apiKey"
            autocomplete="off"
            autofocus
            placeholder="Introduce la API key interna"
            type="password"
          />
        </label>

        <template v-if="authMode === 'firebase'">
          <label>
            Email
            <input
              v-model="email"
              autocomplete="email"
              autofocus
              placeholder="admin@empresa.com"
              type="email"
            />
          </label>

          <label>
            Contraseña
            <input
              v-model="password"
              autocomplete="current-password"
              placeholder="Contraseña"
              type="password"
            />
          </label>
        </template>

        <button
          class="primaryButton"
          type="submit"
          :disabled="authMode === 'firebase' ? !email.trim() || !password : !apiKey.trim()"
        >
          Entrar
        </button>
      </form>
    </section>
  </main>
</template>
