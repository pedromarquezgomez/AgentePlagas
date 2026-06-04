<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '../stores/dashboard'
import DashboardShell from '../components/dashboard/DashboardShell.vue'

const route = useRoute()
const router = useRouter()
const store = useDashboardStore()

const {
  filterChannel,
  filterPestType,
  filterPriority,
  isLoading,
  lastUpdated,
  toasts,
  activeIncidentsCount
} = storeToRefs(store)

// Ocultar filtros si no estamos en una página operativa principal de analíticas/auditoría
const hideFilters = computed(() => {
  const mainDashboards = ['operations', 'analytics', 'ai-performance', 'audit']
  return !mainDashboards.includes(route.name as string)
})

function handleRefresh() {
  void store.triggerRefresh()
}

// Configuración de refresco automático reactivo (polling cada 10 segundos)
let refreshInterval: ReturnType<typeof setInterval> | null = null

function startAutoRefresh() {
  if (refreshInterval) return
  refreshInterval = setInterval(() => {
    // Solo actualizar si la página está activa y visible
    if (document.visibilityState === 'visible') {
      void store.triggerRefresh()
    }
  }, 10000) // cada 10 segundos
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    void store.triggerRefresh() // refrescar inmediatamente al volver a enfocar
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

onMounted(() => {
  startAutoRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopAutoRefresh()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <DashboardShell
    :activeIncidentsCount="activeIncidentsCount"
    :isLoading="isLoading"
    :lastUpdated="lastUpdated"
    v-model:channel="filterChannel"
    v-model:pestType="filterPestType"
    v-model:priority="filterPriority"
    :toasts="toasts"
    :hideFilters="hideFilters"
    @refresh="handleRefresh"
  >
    <!-- Slot de contenido de la página -->
    <RouterView />
  </DashboardShell>
</template>
