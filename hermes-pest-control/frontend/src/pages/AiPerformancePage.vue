<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getRuntimeStats } from '../api/runtime'
import type { RuntimeStats } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import PageHeader from '../components/dashboard/PageHeader.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import LatencyKpiGrid from '../components/dashboard/LatencyKpiGrid.vue'
import TokenUsagePanel from '../components/dashboard/TokenUsagePanel.vue'
import RuntimeModelPanel from '../components/dashboard/RuntimeModelPanel.vue'

// Routing & shell state
const currentPath = ref('/ai-performance')
const isLoading = ref(false)
const isFetching = ref(false)
const lastUpdated = ref('--:--:--')
const errorMsg = ref<string | null>(null)

// Filters state
const filterChannel = ref('all')
const filterPestType = ref('all')
const filterPriority = ref('all')

const stats = ref<RuntimeStats | null>(null)
let autoRefreshInterval: ReturnType<typeof setInterval> | null = null

// Toasts notification system
const toasts = ref<any[]>([])
function showToast(title: string, message: string, type: 'success' | 'error' = 'success') {
  const id = Date.now()
  toasts.value.push({ id, title, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

// Fetch runtime stats from api
async function loadStats(showSpinner = false) {
  if (showSpinner) isLoading.value = true
  isFetching.value = true
  errorMsg.value = null
  try {
    stats.value = await getRuntimeStats()
    const now = new Date()
    lastUpdated.value = now.toTimeString().split(' ')[0]
  } catch (err) {
    console.error('Error cargando estadísticas del runtime:', err)
    if (err instanceof ApiError) {
      errorMsg.value = `Error: ${err.message}`
      showToast('Error de Servidor', err.message, 'error')
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error inesperado al cargar estadísticas'
      showToast('Error', 'No se pudo conectar con la API de ejecución.', 'error')
    }
    stats.value = null
  } finally {
    isLoading.value = false
    isFetching.value = false
  }
}

// Navigate
const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

function handleNavigate(path: string) {
  emit('navigate', path)
}

onMounted(() => {
  loadStats(true)
  // Auto refresh stats every 10 seconds for real-time telemetry
  autoRefreshInterval = setInterval(() => {
    loadStats(false)
  }, 10000)
})

onUnmounted(() => {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval)
  }
})
</script>

<template>
  <DashboardShell
    :currentPath="currentPath"
    :isLoading="isFetching"
    :lastUpdated="lastUpdated"
    v-model:channel="filterChannel"
    v-model:pestType="filterPestType"
    v-model:priority="filterPriority"
    :toasts="toasts"
    @navigate="handleNavigate"
    @refresh="loadStats(true)"
  >
    <div class="performance-content">
      <!-- Error Banner -->
      <ErrorBanner :error="errorMsg" @dismiss="errorMsg = null" />

      <!-- Page Header -->
      <PageHeader 
        title="Métricas de Rendimiento del LLM" 
        subtitle="Latencia, consumo de tokens y tasa de redirección a motor de respaldo (fallback) en tiempo real."
      />

      <!-- Loading State -->
      <LoadingState v-if="isLoading" message="Cargando telemetría de IA..." />

      <template v-else-if="stats">
        <!-- KPIs Grid -->
        <LatencyKpiGrid :stats="stats" />

        <!-- Executive Details Section -->
        <div class="details-section-grid">
          <!-- Token Distribution Card -->
          <TokenUsagePanel 
            :promptTokens="stats.prompt_tokens"
            :completionTokens="stats.completion_tokens"
            :totalTokens="stats.total_tokens"
          />

          <!-- Model Engine Status -->
          <RuntimeModelPanel 
            :provider="stats.provider"
            :model="stats.model"
          />
        </div>
      </template>

      <!-- Empty State -->
      <div v-else-if="!isLoading && !stats" class="empty-state-wrapper">
        <EmptyState message="No hay estadísticas de ejecución disponibles." />
      </div>
    </div>
  </DashboardShell>
</template>

<style scoped>
.performance-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.details-section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}
</style>
