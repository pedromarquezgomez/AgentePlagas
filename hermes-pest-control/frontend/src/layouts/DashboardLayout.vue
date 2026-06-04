<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGlobalState } from '../composables/useGlobalState'
import DashboardShell from '../components/dashboard/DashboardShell.vue'

const route = useRoute()
const router = useRouter()

const {
  filterChannel,
  filterPestType,
  filterPriority,
  isLoading,
  lastUpdated,
  toasts,
  activeIncidentsCount,
  triggerRefresh
} = useGlobalState()

// Ocultar filtros si no estamos en una página operativa principal de analíticas/auditoría
const hideFilters = computed(() => {
  const mainDashboards = ['operations', 'analytics', 'ai-performance', 'audit']
  return !mainDashboards.includes(route.name as string)
})

function handleNavigate(path: string) {
  void router.push(path)
}

function handleRefresh() {
  void triggerRefresh()
}
</script>

<template>
  <DashboardShell
    :currentPath="route.path"
    :activeIncidentsCount="activeIncidentsCount"
    :isLoading="isLoading"
    :lastUpdated="lastUpdated"
    v-model:channel="filterChannel"
    v-model:pestType="filterPestType"
    v-model:priority="filterPriority"
    :toasts="toasts"
    :hideFilters="hideFilters"
    @navigate="handleNavigate"
    @refresh="handleRefresh"
  >
    <!-- Slot de contenido de la página -->
    <RouterView />
  </DashboardShell>
</template>
