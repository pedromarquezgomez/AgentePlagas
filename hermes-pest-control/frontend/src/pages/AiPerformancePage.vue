<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { getRuntimeStats } from '../api/runtime'
import type { RuntimeStats } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'

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

// Prompt & Completion Token Percentages
const promptTokenPercent = computed(() => {
  if (!stats.value || stats.value.total_tokens === 0) return 50
  return Math.round((stats.value.prompt_tokens / stats.value.total_tokens) * 100)
})

const completionTokenPercent = computed(() => {
  return 100 - promptTokenPercent.value
})

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
      <div v-if="stats" class="kpi-grid">
        <KpiCard
          title="Peticiones Realizadas"
          :value="stats.requests"
          description="Invocaciones totales al modelo LLM"
          iconType="comments"
        />
        <KpiCard
          title="Latencia de Inferencia"
          :value="stats.avg_latency_ms + ' ms'"
          description="Tiempo promedio de respuesta del LLM"
          iconType="sla"
          variant="emerald"
        />
        <KpiCard
          title="Fallbacks de Respaldo"
          :value="stats.fallbacks"
          :description="stats.fallbacks > 0 ? 'Redirecciones por error o tiempo límite' : 'Sin redirecciones a motor secundario'"
          iconType="incidents"
          :variant="stats.fallbacks > 0 ? 'danger' : 'default'"
        />
        <KpiCard
          title="Tokens Totales"
          :value="stats.total_tokens"
          description="Volumen total de tokens procesados"
          iconType="cost"
          variant="indigo"
        />
      </div>

      <!-- Executive Details Section -->
      <div v-if="stats" class="details-section-grid">
        <!-- Token Distribution Card -->
        <div class="metrics-block col-span-2">
          <div>
            <h3 class="block-title">Distribución y Consumo de Tokens</h3>
            <p class="block-subtitle">Volumen de datos de entrada frente a datos de salida procesados</p>
          </div>

          <div class="tokens-distribution-container">
            <div class="token-metric-item">
              <div class="token-meta">
                <span class="token-type">Prompt Tokens (Entrada/Contexto)</span>
                <span class="token-count font-mono">{{ stats.prompt_tokens }} ({{ promptTokenPercent }}%)</span>
              </div>
              <div class="token-bar-track">
                <div class="token-bar-fill prompt-fill" :style="{ width: promptTokenPercent + '%' }"></div>
              </div>
            </div>

            <div class="token-metric-item">
              <div class="token-meta">
                <span class="token-type">Completion Tokens (Salida/Generación)</span>
                <span class="token-count font-mono">{{ stats.completion_tokens }} ({{ completionTokenPercent }}%)</span>
              </div>
              <div class="token-bar-track">
                <div class="token-bar-fill completion-fill" :style="{ width: completionTokenPercent + '%' }"></div>
              </div>
            </div>
          </div>
          
          <div class="token-total-footer">
            <span class="total-text font-mono">Consumo Acumulado: {{ stats.total_tokens }} tokens</span>
          </div>
        </div>

        <!-- Model Engine Status -->
        <div class="metrics-block">
          <div>
            <h3 class="block-title">Motor de IA Activo</h3>
            <p class="block-subtitle">Proveedor y modelo de lenguaje actualmente en uso</p>
          </div>

          <div class="engine-status-container">
            <div class="status-pulse-badge">
              <span class="pulse-dot"></span>
              <span class="status-text">ONLINE</span>
            </div>

            <div class="engine-meta-row">
              <span class="meta-label">Proveedor:</span>
              <span class="meta-value uppercase font-mono">{{ stats.provider }}</span>
            </div>

            <div class="engine-meta-row">
              <span class="meta-label">Modelo:</span>
              <span class="meta-value font-mono">{{ stats.model }}</span>
            </div>
          </div>

          <div class="engine-footer-desc">
            Estadísticas recolectadas de forma segura y validadas por el servidor.
          </div>
        </div>
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.details-section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

@media (min-width: 1024px) {
  .col-span-2 {
    grid-column: span 2;
  }
}

.metrics-block {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a;
  margin: 0;
}

.block-subtitle {
  font-size: 10px;
  color: #52525b;
  margin: 4px 0 0 0;
}

.tokens-distribution-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
  flex: 1;
}

.token-metric-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #a1a1aa;
}

.token-type {
  font-weight: 500;
  color: #d4d4d8;
}

.token-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.token-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.prompt-fill {
  background: linear-gradient(90deg, #0284c7, #38bdf8); /* sky-600 to sky-400 */
}

.completion-fill {
  background: linear-gradient(90deg, #7c3aed, #a855f7); /* violet-600 to purple-500 */
}

.token-total-footer {
  margin-top: 16px;
  border-top: 1px solid #27272a;
  padding-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.total-text {
  background: #09090b;
  border: 1px solid #27272a;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 10px;
  color: #e4e4e7;
  font-weight: 700;
}

.engine-status-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
  flex: 1;
}

.status-pulse-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 4px 8px;
  border-radius: 6px;
  align-self: flex-start;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background-color: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-text {
  font-size: 9px;
  font-weight: 800;
  color: #34d399;
  letter-spacing: 0.05em;
}

@keyframes pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.engine-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  border-bottom: 1px solid #27272a;
  padding-bottom: 8px;
}

.meta-label {
  color: #71717a;
}

.meta-value {
  color: #f4f4f5;
  font-weight: 700;
}

.engine-footer-desc {
  font-size: 9px;
  color: #52525b;
  margin-top: 16px;
}
</style>
