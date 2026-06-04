<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import { listIncidents, updateIncident } from '../api/incidents'
import { listToolExecutions, approveToolExecution } from '../api/tools'
import type { Incident, AnalyticsOverview, ToolExecution } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'
import DispatchBucketCard from '../components/dashboard/DispatchBucketCard.vue'
import OperationalIncidentsTable from '../components/dashboard/OperationalIncidentsTable.vue'
import PayloadDrawer from '../components/dashboard/PayloadDrawer.vue'
import type { Toast } from '../components/dashboard/ToastContainer.vue'

// Routing & Shell status
const currentPath = ref('/operations')
const isLoading = ref(false)
const actionLoadingId = ref<string | null>(null)
const lastUpdated = ref('--:--:--')
const errorMsg = ref<string | null>(null)

// Filters state
const filterChannel = ref('all')
const filterPestType = ref('all')
const filterPriority = ref('all')

// Real Data state
const incidents = ref<Incident[]>([])
const metrics = ref<AnalyticsOverview | null>(null)
const proposedTools = ref<ToolExecution[]>([])

// Inspect JSON state
const activePayload = ref<any>(null)
const payloadTitle = ref('')
const isDrawerVisible = ref(false)

// Toasts notification system
const toasts = ref<Toast[]>([])
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
    
    const now = new Date()
    lastUpdated.value = now.toTimeString().split(' ')[0]
  } catch (err) {
    console.error('Error cargando datos en operaciones:', err)
    if (err instanceof ApiError) {
      errorMsg.value = `Error de servidor: ${err.message}`
      showToast('Error de Servidor', err.message, 'error')
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error al conectar con la API.'
      showToast('Error', 'No se pudo conectar con el servidor.', 'error')
    }
  } finally {
    isLoading.value = false
  }
}

// Navigate (propagate navigation to main shell)
const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

function handleNavigate(path: string) {
  emit('navigate', path)
}

// Approve / Confirm action
async function handleApprove(incidentId: string) {
  actionLoadingId.value = incidentId
  try {
    // Buscar si hay una herramienta propuesta asociada al incidente
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
      // Si no hay tool propuesta, avanzar estado del incidente
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

// Close drawer helper
function closeDrawer() {
  isDrawerVisible.value = false
  activePayload.value = null
}

// Computeds for Filters & KPIs
const filteredIncidents = computed(() => {
  return incidents.value.filter(inc => {
    const matchesChannel = filterChannel.value === 'all' || inc.channel === filterChannel.value
    const matchesPest = filterPestType.value === 'all' || inc.pest_type === filterPestType.value
    
    const operationalPriority = inc.operational_priority || inc.priority || ''
    const matchesPriority = filterPriority.value === 'all' || 
      operationalPriority.toUpperCase() === filterPriority.value.toUpperCase()
      
    return matchesChannel && matchesPest && matchesPriority
  })
})

const activeIncidentsCount = computed(() => {
  return filteredIncidents.value.length
})

// Conversion rate based on filtered metrics
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
  refreshData()
})
</script>

<template>
  <DashboardShell
    :currentPath="currentPath"
    :activeIncidentsCount="activeIncidentsCount"
    :isLoading="isLoading"
    :lastUpdated="lastUpdated"
    v-model:channel="filterChannel"
    v-model:pestType="filterPestType"
    v-model:priority="filterPriority"
    :toasts="toasts"
    @navigate="handleNavigate"
    @refresh="refreshData"
  >
    <!-- Main operations screen layout -->
    <div class="operations-dashboard-content">
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

      <!-- Section Title header -->
      <div class="section-header-band">
        <h2 class="section-title">Centro Operativo (HITL)</h2>
        <p class="section-subtitle">Asignaciones recomendadas, estado de SLAs y flujo de control humano de herramientas automatizadas.</p>
      </div>

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
        <div class="metrics-block">
          <h3 class="block-title">Prioridad Operativa</h3>
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
        </div>

        <!-- Severity Donut -->
        <div class="metrics-block donut-block">
          <h3 class="block-title">Severidad Biológica</h3>
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
        </div>

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
    </div>

    <!-- Inspect Drawer component -->
    <PayloadDrawer 
      :payload="activePayload"
      :title="payloadTitle"
      :visible="isDrawerVisible"
      @close="closeDrawer"
    />
  </DashboardShell>
</template>

<style scoped>
.operations-dashboard-content {
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

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
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
  margin: 0 0 16px 0;
}

.progress-stats-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.donut-block {
  justify-content: space-between;
}

.donut-content {
  display: flex;
  align-items: center;
  justify-content: space-around;
  gap: 16px;
  flex: 1;
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
