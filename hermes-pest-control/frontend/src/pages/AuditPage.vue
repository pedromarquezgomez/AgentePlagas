<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { listAuditEvents } from '../api/audit'
import { listToolExecutions, approveToolExecution, rejectToolExecution } from '../api/tools'
import type { AuditEvent, ToolExecution } from '../api/types'
import { ApiError } from '../api/types'

import DashboardShell from '../components/dashboard/DashboardShell.vue'
import AuditKpiGrid from '../components/dashboard/AuditKpiGrid.vue'
import AiDecisionPanel from '../components/dashboard/AiDecisionPanel.vue'
import EventDistributionPanel from '../components/dashboard/EventDistributionPanel.vue'
import GovernanceHealthPanel from '../components/dashboard/GovernanceHealthPanel.vue'
import AuditTimeline from '../components/dashboard/AuditTimeline.vue'
import PendingReviewsPanel from '../components/dashboard/PendingReviewsPanel.vue'
import PayloadDrawer from '../components/dashboard/PayloadDrawer.vue'

// Routing & Shell status
const currentPath = ref('/audit')
const isLoading = ref(false)
const actionLoadingId = ref<string | null>(null)
const lastUpdated = ref('--:--:--')
const errorMsg = ref<string | null>(null)

// Filters state
const filterChannel = ref('all')
const filterPestType = ref('all')
const filterPriority = ref('all')

// Real Data state
const auditEvents = ref<AuditEvent[]>([])
const toolExecutions = ref<ToolExecution[]>([])

// Inspect drawer state
const activePayload = ref<any>(null)
const payloadTitle = ref('')
const isDrawerVisible = ref(false)

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

// Fetch all audit data from API
async function refreshData() {
  isLoading.value = true
  errorMsg.value = null
  try {
    const [eventsList, executionsList] = await Promise.all([
      listAuditEvents(),
      listToolExecutions()
    ])
    auditEvents.value = eventsList
    toolExecutions.value = executionsList

    const now = new Date()
    lastUpdated.value = now.toTimeString().split(' ')[0]
  } catch (err) {
    console.error('Error cargando datos de auditoría:', err)
    if (err instanceof ApiError) {
      errorMsg.value = `Error: ${err.message}`
      showToast('Error de Servidor', err.message, 'error')
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error al conectar con la API de auditoría.'
      showToast('Error', 'No se pudo conectar con el servidor.', 'error')
    }
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

// Action handlers for Pending Reviews
async function handleApprove(id: string) {
  actionLoadingId.value = id
  try {
    await approveToolExecution(id)
    showToast('Ejecución Aprobada', 'La herramienta ha sido autorizada para ejecución segura.', 'success')
    await refreshData()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'No se pudo aprobar la ejecución.'
    showToast('Error', msg, 'error')
  } finally {
    actionLoadingId.value = null
  }
}

async function handleReject(id: string) {
  actionLoadingId.value = id
  try {
    await rejectToolExecution(id)
    showToast('Ejecución Rechazada', 'La ejecución ha sido bloqueada y cancelada.', 'success')
    await refreshData()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'No se pudo rechazar la ejecución.'
    showToast('Error', msg, 'error')
  } finally {
    actionLoadingId.value = null
  }
}

function handleInspect(item: any) {
  activePayload.value = item
  payloadTitle.value = item.event_id 
    ? `Evento #${item.event_id.slice(0, 8).toUpperCase()}`
    : `Ejecución #${item.id.slice(0, 8).toUpperCase()}`
  isDrawerVisible.value = true
}

function closeDrawer() {
  isDrawerVisible.value = false
  activePayload.value = null
}

// Computeds for Filters & KPIs
const filteredEvents = computed(() => {
  return auditEvents.value.filter(e => {
    const matchesChannel = filterChannel.value === 'all' || e.channel === filterChannel.value
    return matchesChannel
  })
})

const filteredExecutions = computed(() => {
  return toolExecutions.value.filter(exec => {
    const matchesChannel = filterChannel.value === 'all' || exec.conversation_id.startsWith(filterChannel.value)
    
    // Priority filter (checks priority inside execution metadata)
    const prio = (exec.metadata?.priority as string || 'NORMAL').toUpperCase()
    const matchesPriority = filterPriority.value === 'all' || 
      prio === filterPriority.value.toUpperCase()

    return matchesChannel && matchesPriority
  })
})

// Metrics calculations
const totalEventsCount = computed(() => filteredEvents.value.length)

const toolsExecutedCount = computed(() => {
  return filteredExecutions.value.filter(e => e.executed).length
})

const pendingHitlCount = computed(() => {
  return filteredExecutions.value.filter(e => e.review_status === 'proposed').length
})

const approvedHitlCount = computed(() => {
  return filteredExecutions.value.filter(e => e.review_status === 'approved').length
})

const rejectedHitlCount = computed(() => {
  return filteredExecutions.value.filter(e => e.review_status === 'rejected').length
})

// Average approval time in seconds
const avgApprovalTime = computed(() => {
  const approvedItems = filteredExecutions.value.filter(e => e.review_status === 'approved' && e.created_at)
  if (approvedItems.length === 0) return 0
  
  let totalDiff = 0
  let count = 0
  approvedItems.forEach(item => {
    const start = new Date(item.created_at!).getTime()
    // Fallback if updated_at / reviewed_at is not defined
    const endStr = item.updated_at || item.created_at
    const end = new Date(endStr!).getTime()
    const diff = (end - start) / 1000
    if (diff >= 0) {
      totalDiff += diff
      count++
    }
  })
  return count > 0 ? totalDiff / count : 0
})

// Backlog (pending > 24 hours)
const backlogCount = computed(() => {
  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000
  return filteredExecutions.value.filter(e => {
    if (e.review_status !== 'proposed' || !e.created_at) return false
    const created = new Date(e.created_at).getTime()
    return (now - created) > oneDayMs
  }).length
})

// Governance risk level calculation
const riskLevel = computed<'HEALTHY' | 'WARNING' | 'CRITICAL'>(() => {
  const bc = backlogCount.value
  const pc = pendingHitlCount.value
  if (bc > 3 || pc > 10) return 'CRITICAL'
  if (bc > 0 || pc > 2) return 'WARNING'
  return 'HEALTHY'
})

const pendingHitlList = computed(() => {
  return filteredExecutions.value.filter(e => e.review_status === 'proposed')
})

onMounted(() => {
  refreshData()
  autoRefreshInterval = setInterval(() => {
    refreshData()
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
    @refresh="refreshData"
  >
    <div class="audit-dashboard-content">
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
        <h2 class="section-title">Centro de Gobierno Operativo & Auditoría</h2>
        <p class="section-subtitle">Trazabilidad en tiempo real de decisiones autónomas del motor de IA y control de gobernanza.</p>
      </div>

      <!-- KPIs Auditoría -->
      <AuditKpiGrid
        :totalEvents="totalEventsCount"
        :toolsExecuted="toolsExecutedCount"
        :pendingHitl="pendingHitlCount"
        :approvedHitl="approvedHitlCount"
        :rejectedHitl="rejectedHitlCount"
      />

      <!-- Middle panels row -->
      <div class="charts-row">
        <!-- Decisiones IA (Donut) -->
        <AiDecisionPanel 
          :approved="approvedHitlCount" 
          :rejected="rejectedHitlCount" 
          :pending="pendingHitlCount" 
        />

        <!-- Eventos por Tipo (Barras Horizontales) -->
        <EventDistributionPanel :events="filteredEvents" />

        <!-- Salud del Gobierno -->
        <GovernanceHealthPanel
          :pendingCount="pendingHitlCount"
          :avgApprovalTimeSeconds="avgApprovalTime"
          :backlogCount="backlogCount"
          :riskLevel="riskLevel"
        />
      </div>

      <!-- Cola Human-In-The-Loop (HITL) -->
      <PendingReviewsPanel
        :pendingReviews="pendingHitlList"
        :loading="isLoading"
        :actionLoadingId="actionLoadingId"
        @approve="handleApprove"
        @reject="handleReject"
        @inspect="handleInspect"
      />

      <!-- Timeline Vivo de Eventos -->
      <AuditTimeline
        :events="filteredEvents"
        :loading="isLoading"
        @inspect-payload="handleInspect"
      />
    </div>

    <!-- Payload drawer -->
    <PayloadDrawer
      :payload="activePayload"
      :title="payloadTitle"
      :visible="isDrawerVisible"
      @close="closeDrawer"
    />
  </DashboardShell>
</template>

<style scoped>
.audit-dashboard-content {
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

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}
</style>
