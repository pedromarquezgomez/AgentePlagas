<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import type { AnalyticsOverview } from '../api/types'
import { useGlobalState } from '../composables/useGlobalState'

import PageHeader from '../components/dashboard/PageHeader.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import AnalyticsKpiGrid from '../components/dashboard/AnalyticsKpiGrid.vue'
import SlaOverviewPanel from '../components/dashboard/SlaOverviewPanel.vue'
import FunnelPanel from '../components/dashboard/FunnelPanel.vue'
import TokenUsagePanel from '../components/dashboard/TokenUsagePanel.vue'

const {
  filterChannel,
  filterPestType,
  onRefresh,
  removeRefresh
} = useGlobalState()

const isLoading = ref(false)
const errorMsg = ref<string | null>(null)
const businessMetrics = ref<AnalyticsOverview | null>(null)

// Fetch analytics from api
async function loadAnalytics() {
  isLoading.value = true
  errorMsg.value = null
  try {
    const params: Record<string, any> = {}
    if (filterChannel.value !== 'all') params.channel = filterChannel.value
    if (filterPestType.value !== 'all') params.pest_type = filterPestType.value

    businessMetrics.value = await getAnalyticsOverview(params)
  } catch (err) {
    console.error('Error cargando métricas:', err)
    errorMsg.value = err instanceof Error ? err.message : 'Error inesperado al cargar métricas'
    businessMetrics.value = null
  } finally {
    isLoading.value = false
  }
}

// React to global filters
watch([filterChannel, filterPestType], () => {
  void loadAnalytics()
})

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

onMounted(() => {
  void loadAnalytics()
  onRefresh(loadAnalytics)
})

onUnmounted(() => {
  removeRefresh(loadAnalytics)
})
</script>

<template>
  <div class="analytics-content">
    <!-- Error Banner -->
    <ErrorBanner :error="errorMsg" @dismiss="errorMsg = null" />

    <!-- Page Header -->
    <PageHeader
      title="Resumen Ejecutivo Global"
      subtitle="Estado consolidado del negocio, facturación simulada, conversiones e incidencias críticas en tiempo real."
    />

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
    </div>

    <!-- Loading State -->
    <LoadingState v-if="isLoading" message="Cargando analíticas del negocio..." />

    <template v-else-if="businessMetrics">
      <!-- KPI Executive Grid -->
      <AnalyticsKpiGrid
        :metrics="businessMetrics"
        :conversionRate="conversionRate"
      />

      <!-- Executive Row Charts / Funnels -->
      <div class="executive-charts-row">
        <!-- SLA Compliance Donut -->
        <SlaOverviewPanel
          :slaComplianceRate="slaComplianceRate"
          :slaOnTimeCount="slaOnTimeCount"
          :slaBreaches="businessMetrics.sla_breaches"
        />

        <!-- Conversion Funnel -->
        <FunnelPanel :funnelData="funnelData" />
      </div>

      <!-- LLM Telemetry Details -->
      <div class="telemetry-section-container">
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
          <TokenUsagePanel
            :promptTokens="businessMetrics.estimated_prompt_tokens"
            :completionTokens="businessMetrics.estimated_completion_tokens"
            :totalTokens="businessMetrics.estimated_total_tokens"
          />
        </div>
      </div>
    </template>

    <!-- Empty State -->
    <div class="empty-state-wrapper" v-else>
      <EmptyState message="No hay métricas de negocio disponibles para los filtros seleccionados." />
    </div>
  </div>
</template>

<style scoped>
.analytics-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
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

.alert-banner-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.executive-charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
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
</style>
