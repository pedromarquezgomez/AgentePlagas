<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  message?: string | null
}>()

const emit = defineEmits<{
  login: [apiKey: string]
}>()

const apiKey = ref('')

function submitLogin(): void {
  const trimmedApiKey = apiKey.value.trim()
  if (!trimmedApiKey) return
  emit('login', trimmedApiKey)
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
        <label>
          API key
          <input
            v-model="apiKey"
            autocomplete="off"
            autofocus
            placeholder="Introduce la API key interna"
            type="password"
          />
        </label>

        <button class="primaryButton" type="submit" :disabled="!apiKey.trim()">
          Entrar
        </button>
      </form>
    </section>
  </main>
</template>
