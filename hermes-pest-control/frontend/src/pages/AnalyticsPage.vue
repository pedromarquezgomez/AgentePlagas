<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import type { AnalyticsOverview } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'

// Routing & shell state
const currentPath = ref('/analytics')
const isLoading = ref(false)
const lastUpdated = ref('--:--:--')
const errorMsg = ref<string | null>(null)

// Filters state
const filterChannel = ref('all')
const filterPestType = ref('all')
const filterPriority = ref('all') // not used in metrics api, but unifies shell v-model

const businessMetrics = ref<AnalyticsOverview | null>(null)

// Toasts notification system
const toasts = ref<any[]>([])
function showToast(title: string, message: string, type: 'success' | 'error' = 'success') {
  const id = Date.now()
  toasts.value.push({ id, title, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

// Fetch analytics from api
async function loadAnalytics() {
  isLoading.value = true
  errorMsg.value = null
  try {
    const params: Record<string, any> = {}
    if (filterChannel.value !== 'all') params.channel = filterChannel.value
    if (filterPestType.value !== 'all') params.pest_type = filterPestType.value

    businessMetrics.value = await getAnalyticsOverview(params)
    
    const now = new Date()
    lastUpdated.value = now.toTimeString().split(' ')[0]
  } catch (err) {
    console.error('Error cargando métricas:', err)
    if (err instanceof ApiError) {
      errorMsg.value = `Error: ${err.message}`
      showToast('Error de Servidor', err.message, 'error')
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error inesperado al cargar métricas'
      showToast('Error', 'No se pudo conectar con la API.', 'error')
    }
    businessMetrics.value = null
  } finally {
    isLoading.value = false
  }
}

// Propagate navigation
const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

function handleNavigate(path: string) {
  emit('navigate', path)
}

// React to filters
function handleFilterChange() {
  loadAnalytics()
}

// Computeds for secondary charts
const slaComplianceRate = computed(() => {
  if (!businessMetrics.value) return 100
  const total = businessMetrics.value.incidents_created
  if (total === 0) return 100
  const onTime = total - businessMetrics.value.sla_breaches
  return Math.round((onTime / total) * 100)
})

const slaOnTimeCount = computed(() => {
  if (!businessMetrics.value) return 0
  return Math.max(0, businessMetrics.value.incidents_created - businessMetrics.value.sla_breaches)
})

// Conversion rate
const conversionRate = computed(() => {
  if (!businessMetrics.value) return '0.0'
  const total = businessMetrics.value.total_conversations
  const created = businessMetrics.value.incidents_created
  if (total === 0) return '0.0'
  return ((created / total) * 100).toFixed(1)
})

// Funnel calculations
const funnelData = computed(() => {
  if (!businessMetrics.value) return []
  
  const total = businessMetrics.value.total_conversations || 1
  const created = businessMetrics.value.incidents_created
  const proposed = businessMetrics.value.visits_proposed
  const confirmed = businessMetrics.value.visits_confirmed
  const closed = businessMetrics.value.closed_incidents

  return [
    { label: '1. Conversaciones Iniciales', value: total, percent: 100, icon: 'comments' },
    { label: '2. Incidencias Creadas', value: created, percent: Math.round((created / total) * 100), icon: 'incidents' },
    { label: '3. Visitas Propuestas', value: proposed, percent: Math.round((proposed / total) * 100), icon: 'proposed' },
    { label: '4. Visitas Confirmadas', value: confirmed, percent: Math.round((confirmed / total) * 100), icon: 'confirmed' },
    { label: '5. Casos Cerrados', value: closed, percent: Math.round((closed / total) * 100), icon: 'closed' }
  ]
})

// Token percentages
const promptTokenPercent = computed(() => {
  if (!businessMetrics.value) return 50
  const total = businessMetrics.value.estimated_total_tokens
  if (total === 0) return 50
  return Math.round((businessMetrics.value.estimated_prompt_tokens / total) * 100)
})

const completionTokenPercent = computed(() => {
  return 100 - promptTokenPercent.value
})

onMounted(() => {
  loadAnalytics()
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
    @update:channel="handleFilterChange"
    @update:pestType="handleFilterChange"
    @navigate="handleNavigate"
    @refresh="loadAnalytics"
  >
    <div class="analytics-content">
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

      <!-- Alert Banners -->
      <div v-if="businessMetrics" class="alerts-section">
        <div 
          v-if="businessMetrics.sla_breaches > 0" 
          class="alert-banner alert-critical"
        >
          <svg class="alert-banner-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          ALERTA CRÍTICA: Se han detectado {{ businessMetrics.sla_breaches }} incumplimientos de SLA en incidencias.
        </div>
        <div 
          v-else-if="businessMetrics.avg_llm_latency_ms > 5000" 
          class="alert-banner alert-warning"
        >
          <svg class="alert-banner-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          ADVERTENCIA: Latencia media del LLM alta ({{ businessMetrics.avg_llm_latency_ms }} ms).
        </div>
      </div>

      <!-- Section title -->
      <div class="section-header-band">
        <h2 class="section-title">Resumen Ejecutivo Global</h2>
        <p class="section-subtitle">Estado consolidado del negocio, facturación simulada, conversiones e incidencias críticas en tiempo real.</p>
      </div>

      <!-- KPI Executive Grid -->
      <div v-if="businessMetrics" class="kpi-grid">
        <KpiCard 
          title="Conversaciones Totales"
          :value="businessMetrics.total_conversations"
          description="Acumulado total de mensajes recibidos"
          iconType="comments"
        />
        <KpiCard 
          title="Incidencias Creadas"
          :value="businessMetrics.incidents_created"
          :description="`Cerradas: ${businessMetrics.closed_incidents} | Canceladas: ${businessMetrics.cancelled_incidents}`"
          iconType="incidents"
        />
        <KpiCard 
          title="Tasa de Conversión AI"
          :value="conversionRate + '%'"
          :progressValue="parseFloat(conversionRate)"
          description="Efectividad en creación de incidencias"
          iconType="conversion"
          variant="emerald"
        />
        <KpiCard 
          title="Inversión Coste IA"
          :value="'$' + businessMetrics.estimated_llm_cost_usd.toFixed(3)"
          description="Acumulado por consumo de tokens"
          iconType="cost"
          variant="indigo"
        />
      </div>

      <!-- Executive Row Charts / Funnels -->
      <div v-if="businessMetrics" class="executive-charts-row">
        <!-- SLA Compliance Donut -->
        <div class="metrics-block flex-between">
          <div>
            <h3 class="block-title">Cumplimiento General SLA</h3>
            <p class="block-subtitle">Métricas de cumplimiento calculadas por el backend</p>
          </div>
          
          <div class="radial-chart-wrapper">
            <div class="radial-svg-wrapper">
              <svg class="radial-svg" viewBox="0 0 36 36">
                <path class="radial-bg" stroke-width="3" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="radial-fill" stroke-width="4.5" :stroke-dasharray="`${slaComplianceRate}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div class="radial-labels">
                <span class="radial-value">{{ slaComplianceRate }}%</span>
                <span class="radial-sub">On-Time</span>
              </div>
            </div>
          </div>

          <div class="radial-legend">
            <div class="legend-item">
              <span class="legend-dot green"></span>
              <span class="legend-text">En plazo ({{ slaOnTimeCount }})</span>
            </div>
            <div class="legend-item">
              <span class="legend-dot red"></span>
              <span class="legend-text">Vencidos ({{ businessMetrics.sla_breaches }})</span>
            </div>
          </div>
        </div>

        <!-- Conversion Funnel -->
        <div class="metrics-block col-span-2">
          <div>
            <h3 class="block-title">Embudo Operativo & Automatización</h3>
            <p class="block-subtitle">Conversión automatizada de interacciones conversacionales</p>
          </div>

          <div class="funnel-steps-list">
            <div v-for="step in funnelData" :key="step.label" class="funnel-step">
              <div class="funnel-step-meta">
                <span class="step-label-text">
                  <svg v-if="step.icon === 'comments'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" /></svg>
                  <svg v-else-if="step.icon === 'incidents'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
                  <svg v-else-if="step.icon === 'proposed'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" /></svg>
                  <svg v-else-if="step.icon === 'confirmed'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  <svg v-else class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.746 3.746 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" /></svg>
                  {{ step.label }}
                </span>
                <span class="step-value-text font-mono">{{ step.value }} ({{ step.percent }}%)</span>
              </div>
              <div class="step-bar-track">
                <div class="step-bar-fill" :style="{ width: step.percent + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- LLM Telemetry Details -->
      <div v-if="businessMetrics" class="telemetry-section-container">
        <div class="telemetry-header">
          <h3 class="telemetry-title">Detalle y Telemetría del LLM</h3>
          <p class="telemetry-subtitle">Consumo de recursos, tokens y latencia de inferencia</p>
        </div>

        <div class="telemetry-grid">
          <!-- Latencia -->
          <div class="telemetry-card">
            <span class="card-label">Latencia Media Inferencia</span>
            <div class="card-value-container">
              <span class="card-value emerald">{{ businessMetrics.avg_llm_latency_ms }}</span>
              <span class="card-unit">ms</span>
            </div>
            <p class="card-desc">Tiempo de respuesta medio del LLM</p>
          </div>

          <!-- Fallbacks -->
          <div class="telemetry-card">
            <span class="card-label">Llamadas de Fallback</span>
            <div class="card-value-container">
              <span class="card-value" :class="businessMetrics.fallback_count > 0 ? 'amber' : 'default'">
                {{ businessMetrics.fallback_count }}
              </span>
            </div>
            <p class="card-desc">Redirecciones a motor de respaldo</p>
          </div>

          <!-- Tokens Breakdown -->
          <div class="telemetry-card col-span-2 flex-between">
            <div class="tokens-header">
              <span class="card-label">Distribución de Tokens Consumidos</span>
            </div>
            
            <div class="tokens-bars">
              <div class="token-item-bar">
                <div class="token-meta">
                  <span>Prompt Tokens (Entrada)</span>
                  <span class="font-mono">{{ businessMetrics.estimated_prompt_tokens }}</span>
                </div>
                <div class="token-track">
                  <div class="token-fill sky" :style="{ width: promptTokenPercent + '%' }"></div>
                </div>
              </div>
              
              <div class="token-item-bar">
                <div class="token-meta">
                  <span>Completion Tokens (Salida)</span>
                  <span class="font-mono">{{ businessMetrics.estimated_completion_tokens }}</span>
                </div>
                <div class="token-track">
                  <div class="token-fill purple" :style="{ width: completionTokenPercent + '%' }"></div>
                </div>
              </div>
            </div>

            <div class="token-summary-badge font-mono">
              Total Tokens: {{ businessMetrics.estimated_total_tokens }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </DashboardShell>
</template>

<style scoped>
.analytics-content {
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

.alerts-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.alert-critical {
  background: rgba(127, 29, 29, 0.15);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.2);
}

.alert-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.2);
}

.alert-banner-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
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

.executive-charts-row {
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

.flex-between {
  justify-content: space-between;
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

.radial-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 20px 0;
}

.radial-svg-wrapper {
  position: relative;
  width: 112px;
  height: 112px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radial-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.radial-bg {
  fill: none;
  stroke: #27272a;
}

.radial-fill {
  fill: none;
  stroke: #10b981; /* emerald-500 */
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.radial-labels {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.radial-value {
  font-size: 26px;
  font-weight: 800;
  color: #f4f4f5;
  line-height: 1;
}

.radial-sub {
  font-size: 8px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  margin-top: 2px;
  font-weight: 600;
}

.radial-legend {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  border-top: 1px solid #27272a;
  padding-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.green {
  background: #10b981;
}

.legend-dot.red {
  background: #ef4444;
}

.legend-text {
  color: #a1a1aa;
}

.funnel-steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.funnel-step {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.funnel-step-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  align-items: center;
}

.step-label-text {
  color: #d4d4d8;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-icon {
  width: 14px;
  height: 14px;
  color: #52525b;
}

.step-value-text {
  font-weight: 700;
  color: #f4f4f5;
}

.step-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.step-bar-fill {
  background: linear-gradient(90deg, #059669, #14b8a6); /* emerald-600 to teal-500 */
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.telemetry-section-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 12px;
}

.telemetry-header {
  border-bottom: 1px solid #18181b;
  padding-bottom: 8px;
}

.telemetry-title {
  font-size: 14px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.telemetry-subtitle {
  font-size: 11px;
  color: #71717a;
  margin: 2px 0 0 0;
}

.telemetry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.telemetry-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100px;
}

.card-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a;
}

.card-value-container {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 8px;
}

.card-value {
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
}

.card-value.default {
  color: #f4f4f5;
}

.card-value.emerald {
  color: #34d399;
}

.card-value.amber {
  color: #fbbf24;
}

.card-unit {
  font-size: 12px;
  font-weight: 700;
  color: #52525b;
}

.card-desc {
  font-size: 10px;
  color: #71717a;
  margin: 8px 0 0 0;
}

.tokens-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  margin: 12px 0;
}

.token-item-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.token-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #a1a1aa;
}

.token-track {
  background: #09090b;
  height: 6px;
  border-radius: 9999px;
  overflow: hidden;
}

.token-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.token-fill.sky {
  background: #38bdf8;
}

.token-fill.purple {
  background: #a855f7;
}

.token-summary-badge {
  background: #09090b;
  border: 1px solid #27272a;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #e4e4e7;
  text-align: center;
  width: 100%;
}
</style>
