<script setup lang="ts">
import { computed } from 'vue'
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
