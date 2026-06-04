<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getRuntimeStats } from '../api/runtime'
import type { RuntimeStats } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import LatencyKpiGrid from '../components/dashboard/LatencyKpiGrid.vue'
import TokenUsagePanel from '../components/dashboard/TokenUsagePanel.vue'
import RuntimeModelPanel from '../components/dashboard/RuntimeModelPanel.vue'

// Routing & shell state
const currentPath = ref('/ai-performance')
const isLoading = ref(false)
const lastUpdated = ref('--:--:--')
const errorMsg = ref<string | null>(null)

// Filters state (unified with other dashboard layouts)
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
async function loadStats() {
  isLoading.value = true
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
  loadStats()
  // Auto refresh stats every 10 seconds for real-time telemetry
  autoRefreshInterval = setInterval(() => {
    loadStats()
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
    :isLoading="isLoading"
    :lastUpdated="lastUpdated"
    v-model:channel="filterChannel"
    v-model:pestType="filterPestType"
    v-model:priority="filterPriority"
    :toasts="toasts"
    @navigate="handleNavigate"
    @refresh="loadStats"
  >
    <div class="performance-content">
      <!-- Error Bar -->
      <div v-if="errorMsg" class="error-bar">
        <div class="error-left">
          <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <span>{{ errorMsg }}</span>
        </div>
        <button class="dismiss-btn" @click="errorMsg = null">Descartar</button>
      </div>

      <!-- Section Title -->
      <div class="section-header-band">
        <h2 class="section-title">Métricas de Rendimiento del LLM</h2>
        <p class="section-subtitle">Latencia, consumo de tokens y tasa de redirección a motor de respaldo (fallback) en tiempo real.</p>
      </div>

      <!-- KPIs Grid -->
      <LatencyKpiGrid :stats="stats" />

      <!-- Executive Details Section -->
      <div v-if="stats" class="details-section-grid">
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
    </div>
  </DashboardShell>
</template>

<style scoped>
.performance-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.error-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(127, 29, 29, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fee2e2;
  font-size: 13px;
}

.error-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-icon {
  width: 18px;
  height: 18px;
  color: #f87171;
}

.dismiss-btn {
  background: transparent;
  border: none;
  color: #f87171;
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  cursor: pointer;
  text-decoration: underline;
}

.section-header-band {
  border-bottom: 1px solid #18181b;
  padding-bottom: 12px;
}

.section-title {
  font-size: 20px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.section-subtitle {
  font-size: 12px;
  color: #a1a1aa;
  margin: 4px 0 0 0;
}

.details-section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}
</style>
