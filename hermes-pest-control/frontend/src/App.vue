<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { observeAuthState, AUTH_MODE, REQUIRE_LOGIN, getStoredAuthIndicator } from './services/api'

const router = useRouter()
let stopAuthObserver: (() => void) | null = null

onMounted(() => {
  stopAuthObserver = observeAuthState((hasAuthAccess) => {
    if (AUTH_MODE !== 'firebase') return
    const adminApiKey = hasAuthAccess ? getStoredAuthIndicator() : ''
    const hasAccess = !REQUIRE_LOGIN || Boolean(adminApiKey)

    if (REQUIRE_LOGIN && !hasAccess && router.currentRoute.value.name !== 'login') {
      void router.push('/login')
    } else if (REQUIRE_LOGIN && hasAccess && router.currentRoute.value.name === 'login') {
      void router.push('/operations')
    }
  })
})

onUnmounted(() => {
  if (stopAuthObserver) stopAuthObserver()
})
</script>

<template>
  <RouterView />
</template>
