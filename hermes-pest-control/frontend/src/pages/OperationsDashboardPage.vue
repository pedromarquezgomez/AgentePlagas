<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import { listIncidents, updateIncident } from '../api/incidents'
import { listToolExecutions, approveToolExecution } from '../api/tools'
import type { Incident, AnalyticsOverview, ToolExecution } from '../api/types'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '../stores/dashboard'
import { normalizePestType } from '../utils/labels'
import { useEventStream } from '../composables/useEventStream'

import PageHeader from '../components/dashboard/PageHeader.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import SectionCard from '../components/dashboard/SectionCard.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'
import DispatchBucketCard from '../components/dashboard/DispatchBucketCard.vue'
import OperationalIncidentsTable from '../components/dashboard/OperationalIncidentsTable.vue'
import PayloadDrawer from '../components/dashboard/PayloadDrawer.vue'

const store = useDashboardStore()
const {
  filterChannel,
  filterPestType,
  filterPriority,
  activeIncidentsCount,
  toasts
} = storeToRefs(store)
const { onRefresh, removeRefresh } = store

const isLoading = ref(false)
const actionLoadingId = ref<string | null>(null)
const errorMsg = ref<string | null>(null)

// Real Data state
const incidents = ref<Incident[]>([])
const metrics = ref<AnalyticsOverview | null>(null)
const proposedTools = ref<ToolExecution[]>([])

// Inspect JSON state
const activePayload = ref<any>(null)
const payloadTitle = ref('')
const isDrawerVisible = ref(false)

function showToast(title: string, message: string, type: 'success' | 'error' = 'success') {
  const id = Date.now()
  toasts.value.push({ id, title, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

// Fetch all data from APIs
async function refreshData() {
  isLoading.value = true
  errorMsg.value = null
  try {
    const [incList, metData, toolList] = await Promise.all([
      listIncidents(),
      getAnalyticsOverview(),
      listToolExecutions({ review_status: 'proposed' })
    ])
    incidents.value = incList
    metrics.value = metData
    proposedTools.value = toolList
  } catch (err) {
    console.error('Error cargando datos en operaciones:', err)
    errorMsg.value = err instanceof Error ? err.message : 'Error al conectar con la API.'
    showToast('Error', 'No se pudo conectar con el servidor.', 'error')
  } finally {
    isLoading.value = false
  }
}

// React to filters
watch([filterChannel, filterPestType, filterPriority], () => {
  void refreshData()
})

// Approve / Confirm action
async function handleApprove(incidentId: string) {
  actionLoadingId.value = incidentId
  try {
    const inc = incidents.value.find(i => i.id === incidentId)
    const tool = proposedTools.value.find(t => 
      t.metadata?.incident_id === incidentId || 
      (inc && t.conversation_id === inc.conversation_id)
    )

    if (tool) {
      await approveToolExecution(tool.id)
      showToast(
        'Propuesta Aprobada', 
        `Se aprobó la ejecución de ${tool.tool_name} de forma segura.`,
        'success'
      )
    } else {
      await updateIncident(incidentId, { status: 'ready_for_scheduling' })
      showToast(
        'Incidencia Confirmada',
        'El estado de la incidencia ha cambiado a listo para agendar.',
        'success'
      )
    }
    await refreshData()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'No se pudo confirmar la acción.'
    showToast('Error', msg, 'error')
  } finally {
    actionLoadingId.value = null
  }
}

// Cancel / Reject action
async function handleCancel(incidentId: string) {
  actionLoadingId.value = incidentId
  try {
    await updateIncident(incidentId, { status: 'cancelled' })
    showToast(
      'Incidencia Cancelada',
      'El estado de la incidencia se ha actualizado a cancelado.',
      'success'
    )
    await refreshData()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'No se pudo cancelar el caso.'
    showToast('Error', msg, 'error')
  } finally {
    actionLoadingId.value = null
  }
}

// Open Drawer to inspect payload
function handleInspect(incident: Incident) {
  activePayload.value = incident
  payloadTitle.value = `Incidencia #${incident.id.slice(0, 8).toUpperCase()}`
  isDrawerVisible.value = true
}

function closeDrawer() {
  isDrawerVisible.value = false
  activePayload.value = null
}

// Computeds for Filters & KPIs
const filteredIncidents = computed(() => {
  return incidents.value.filter(inc => {
    const matchesChannel = filterChannel.value === 'all' || inc.channel === filterChannel.value
    const matchesPest = filterPestType.value === 'all' || 
      normalizePestType(inc.pest_type) === filterPestType.value
    
    const operationalPriority = inc.operational_priority || inc.priority || ''
    const matchesPriority = filterPriority.value === 'all' || 
      operationalPriority.toUpperCase() === filterPriority.value.toUpperCase()
      
    return matchesChannel && matchesPest && matchesPriority
  })
})

// Sync count of incidents globally
watch(filteredIncidents, (newVal) => {
  activeIncidentsCount.value = newVal.length
}, { immediate: true })

const conversionRate = computed(() => {
  const total = metrics.value?.total_conversations || 0
  const created = metrics.value?.incidents_created || 0
  if (total === 0) return '0.0'
  return ((created / total) * 100).toFixed(1)
})

// Secondary charts and lists
const priorityStats = computed(() => {
  const counts = { URGENT: 0, HIGH: 0, NORMAL: 0, LOW: 0 }
  filteredIncidents.value.forEach(i => {
    const prio = (i.operational_priority || i.priority || 'NORMAL').toUpperCase()
    if (prio === 'URGENT') counts.URGENT++
    else if (prio === 'HIGH') counts.HIGH++
    else if (prio === 'NORMAL' || prio === 'MEDIUM') counts.NORMAL++
    else counts.LOW++
  })
  
  const total = filteredIncidents.value.length || 1
  return [
    { name: 'Urgente', count: counts.URGENT, percentage: (counts.URGENT / total) * 100, colorBg: 'bg-red', colorText: 'text-red' },
    { name: 'Alta', count: counts.HIGH, percentage: (counts.HIGH / total) * 100, colorBg: 'bg-amber', colorText: 'text-amber' },
    { name: 'Normal', count: counts.NORMAL, percentage: (counts.NORMAL / total) * 100, colorBg: 'bg-sky', colorText: 'text-sky' }
  ]
})

const severityCounts = computed(() => {
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }
  filteredIncidents.value.forEach(i => {
    const sev = (i.severity || 'LOW').toUpperCase()
    if (sev === 'CRITICAL') counts.CRITICAL++
    else if (sev === 'HIGH') counts.HIGH++
    else if (sev === 'MEDIUM') counts.MEDIUM++
    else counts.LOW++
  })
  return counts
})

const severityPercentages = computed(() => {
  const total = filteredIncidents.value.length || 1
  return {
    critical: (severityCounts.value.CRITICAL / total) * 100,
    high: (severityCounts.value.HIGH / total) * 100,
    medium: (severityCounts.value.MEDIUM / total) * 100,
    low: (severityCounts.value.LOW / total) * 100,
  }
})

const dispatchBuckets = computed(() => {
  const counts: Record<string, number> = { URGENT_24H: 0, THIS_WEEK: 0, MANUAL_REVIEW: 0 }
  filteredIncidents.value.forEach(i => {
    const bucket = i.dispatch_bucket || 'MANUAL_REVIEW'
    if (counts[bucket] !== undefined) {
      counts[bucket]++
    } else {
      counts.MANUAL_REVIEW++
    }
  })
  
  return [
    { name: 'Urgente 24 Horas', count: counts.URGENT_24H, code: 'URGENT_24H' },
    { name: 'Agenda Semanal', count: counts.THIS_WEEK, code: 'THIS_WEEK' },
    { name: 'Revisión Manual', count: counts.MANUAL_REVIEW, code: 'MANUAL_REVIEW' }
  ]
})

onMounted(() => {
  void refreshData()
  onRefresh(refreshData)
})

onUnmounted(() => {
  removeRefresh(refreshData)
})

useEventStream((event) => {
  const refreshEvents = [
    'incident_created',
    'incident_updated',
    'incident_cancelled',
    'tool_proposed',
    'tool_review_updated',
    'tool_execution_completed',
    'sla_breached',
    'calendar_visit_proposed'
  ]
  if (refreshEvents.includes(event.event_type)) {
    void refreshData()
  }
})
</script>

<template>
  <div class="operations-dashboard-content">
    <!-- Error Banner -->
    <ErrorBanner :error="errorMsg" @dismiss="errorMsg = null" />

    <!-- Page Header -->
    <PageHeader
      title="Centro Operativo (HITL)"
      subtitle="Asignaciones recomendadas, estado de SLAs y flujo de control humano de herramientas automatizadas."
    />

    <!-- Loading State -->
    <LoadingState v-if="isLoading" message="Cargando centro operativo..." />

    <template v-else-if="incidents.length > 0">
      <!-- KPI Executive widgets grid -->
      <div class="kpi-grid">
        <KpiCard
          title="Conversaciones Totales"
          :value="metrics?.total_conversations ?? 0"
          description="Acumulado en últimos 30 días"
          iconType="comments"
        />
        <KpiCard
          title="Incidencias Creadas"
          :value="incidents.length"
          description="Registradas por el Intake Engine"
          iconType="incidents"
        />
        <KpiCard
          title="Tasa de Conversión AI"
          :value="conversionRate + '%'"
          :progressValue="parseFloat(conversionRate)"
          description="Conversión de chats a incidencias"
          iconType="conversion"
          variant="emerald"
        />
        <KpiCard
          title="Inversión Coste IA"
          :value="'$' + (metrics?.estimated_llm_cost_usd ?? 0.0).toFixed(3)"
          description="Estimado por consumo de tokens"
          iconType="cost"
          variant="indigo"
        />
      </div>

      <!-- Secondary metrics grid -->
      <div class="charts-row">
        <!-- Priority Card -->
        <SectionCard
          title="Prioridad Operativa"
          subtitle="Gravedad de atención de casos en tiempo real"
        >
          <div class="progress-stats-list">
            <div v-for="item in priorityStats" :key="item.name" class="progress-stat-item">
              <div class="stat-meta">
                <span class="stat-name">{{ item.name }}</span>
                <span class="stat-count" :class="item.colorText">{{ item.count }} casos</span>
              </div>
              <div class="stat-bar-track">
                <div class="stat-bar-fill" :class="item.colorBg" :style="{ width: item.percentage + '%' }"></div>
              </div>
            </div>
          </div>
        </SectionCard>

        <!-- Severity Donut -->
        <SectionCard
          title="Severidad Biológica"
          subtitle="Clasificación del tipo de plaga y área afectada"
        >
          <div class="donut-content">
            <div class="donut-svg-wrapper">
              <svg class="donut-svg" viewBox="0 0 36 36">
                <path class="donut-bg" stroke-width="4" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="donut-fill" stroke-width="4.5" :stroke-dasharray="`${severityPercentages.critical}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div class="donut-labels">
                <span class="donut-value">{{ incidents.length }}</span>
                <span class="donut-sub">Casos</span>
              </div>
            </div>
            <div class="donut-legend">
              <div class="legend-item"><span class="legend-dot critical"></span> Crítica ({{ severityCounts.CRITICAL }})</div>
              <div class="legend-item"><span class="legend-dot high"></span> Alta ({{ severityCounts.HIGH }})</div>
              <div class="legend-item"><span class="legend-dot medium"></span> Media ({{ severityCounts.MEDIUM }})</div>
              <div class="legend-item"><span class="legend-dot low"></span> Baja ({{ severityCounts.LOW }})</div>
            </div>
          </div>
        </SectionCard>

        <!-- Dispatch Buckets -->
        <DispatchBucketCard :buckets="dispatchBuckets" />
      </div>

      <!-- Master Incidents table component -->
      <OperationalIncidentsTable
        :incidents="filteredIncidents"
        :loading="isLoading"
        :actionLoadingId="actionLoadingId"
        @approve="handleApprove"
        @cancel="handleCancel"
        @inspect="handleInspect"
      />
    </template>

    <!-- Empty State -->
    <div v-else class="empty-state-wrapper">
      <EmptyState message="No hay incidencias registradas en el Centro Operativo." />
    </div>
  </div>

  <!-- Inspect Drawer component -->
  <PayloadDrawer
    :payload="activePayload"
    :title="payloadTitle"
    :visible="isDrawerVisible"
    @close="closeDrawer"
  />
</template>

<style scoped>
.operations-dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.progress-stats-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 4px;
}

.progress-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-name {
  color: #d4d4d8;
  font-weight: 500;
}

.stat-count {
  font-weight: 700;
}

.stat-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease-out;
}

.bg-red {
  background: #ef4444;
}

.bg-amber {
  background: #f59e0b;
}

.bg-sky {
  background: #0ea5e9;
}

.text-red {
  color: #f87171;
}

.text-amber {
  color: #fbbf24;
}

.text-sky {
  color: #38bdf8;
}

.donut-content {
  display: flex;
  align-items: center;
  justify-content: space-around;
  gap: 16px;
  flex: 1;
  margin-top: 4px;
}

.donut-svg-wrapper {
  position: relative;
  width: 96px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-bg {
  fill: none;
  stroke: #27272a;
}

.donut-fill {
  fill: none;
  stroke: #ef4444;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.donut-labels {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-value {
  font-size: 24px;
  font-weight: 800;
  color: #f4f4f5;
  line-height: 1;
}

.donut-sub {
  font-size: 9px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  margin-top: 2px;
}

.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #d4d4d8;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.critical {
  background: #ef4444;
}

.legend-dot.high {
  background: #f59e0b;
}

.legend-dot.medium {
  background: #0ea5e9;
}

.legend-dot.low {
  background: #71717a;
}
</style>


<style scoped>
.operations-dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.progress-stats-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 4px;
}

.progress-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-name {
  color: #d4d4d8;
  font-weight: 500;
}

.stat-count {
  font-weight: 700;
}

.stat-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease-out;
}

.bg-red {
  background: #ef4444;
}

.bg-amber {
  background: #f59e0b;
}

.bg-sky {
  background: #0ea5e9;
}

.text-red {
  color: #f87171;
}

.text-amber {
  color: #fbbf24;
}

.text-sky {
  color: #38bdf8;
}

.donut-content {
  display: flex;
  align-items: center;
  justify-content: space-around;
  gap: 16px;
  flex: 1;
  margin-top: 4px;
}

.donut-svg-wrapper {
  position: relative;
  width: 96px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-bg {
  fill: none;
  stroke: #27272a;
}

.donut-fill {
  fill: none;
  stroke: #ef4444;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.donut-labels {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-value {
  font-size: 24px;
  font-weight: 800;
  color: #f4f4f5;
  line-height: 1;
}

.donut-sub {
  font-size: 9px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  margin-top: 2px;
}

.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #d4d4d8;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.critical {
  background: #ef4444;
}

.legend-dot.high {
  background: #f59e0b;
}

.legend-dot.medium {
  background: #0ea5e9;
}

.legend-dot.low {
  background: #71717a;
}
</style>
