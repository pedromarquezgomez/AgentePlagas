<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getRuntimeStats } from '../api/runtime'
import type { RuntimeStats } from '../api/types'
import { useGlobalState } from '../composables/useGlobalState'

import PageHeader from '../components/dashboard/PageHeader.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import LatencyKpiGrid from '../components/dashboard/LatencyKpiGrid.vue'
import TokenUsagePanel from '../components/dashboard/TokenUsagePanel.vue'
import RuntimeModelPanel from '../components/dashboard/RuntimeModelPanel.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'

const { onRefresh, removeRefresh } = useGlobalState()

const isLoading = ref(false)
const errorMsg = ref<string | null>(null)
const stats = ref<RuntimeStats | null>(null)
let autoRefreshInterval: ReturnType<typeof setInterval> | null = null

// Fetch runtime stats from api
async function loadStats() {
  isLoading.value = true
  errorMsg.value = null
  try {
    stats.value = await getRuntimeStats()
  } catch (err) {
    console.error('Error cargando estadísticas del runtime:', err)
    errorMsg.value = err instanceof Error ? err.message : 'Error inesperado al cargar estadísticas'
    stats.value = null
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  void loadStats()
  onRefresh(loadStats)
  // Auto refresh stats every 10 seconds for real-time telemetry
  autoRefreshInterval = setInterval(() => {
    void loadStats()
  }, 10000)
})

onUnmounted(() => {
  removeRefresh(loadStats)
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval)
  }
})
</script>

<template>
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
    <div v-else class="empty-state-wrapper">
      <EmptyState message="No hay estadísticas de ejecución disponibles." />
    </div>
  </div>
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
