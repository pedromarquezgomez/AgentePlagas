<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { listAuditEvents } from '../api/audit'
import { listToolExecutions, approveToolExecution, rejectToolExecution } from '../api/tools'
import type { AuditEvent, ToolExecution } from '../api/types'
import { useGlobalState } from '../composables/useGlobalState'

import PageHeader from '../components/dashboard/PageHeader.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import AuditKpiGrid from '../components/dashboard/AuditKpiGrid.vue'
import AiDecisionPanel from '../components/dashboard/AiDecisionPanel.vue'
import EventDistributionPanel from '../components/dashboard/EventDistributionPanel.vue'
import GovernanceHealthPanel from '../components/dashboard/GovernanceHealthPanel.vue'
import AuditTimeline from '../components/dashboard/AuditTimeline.vue'
import PendingReviewsPanel from '../components/dashboard/PendingReviewsPanel.vue'
import PayloadDrawer from '../components/dashboard/PayloadDrawer.vue'

const {
  filterChannel,
  filterPestType,
  filterPriority,
  onRefresh,
  removeRefresh,
  toasts
} = useGlobalState()

const isLoading = ref(false)
const actionLoadingId = ref<string | null>(null)
const errorMsg = ref<string | null>(null)

// Real Data state
const auditEvents = ref<AuditEvent[]>([])
const toolExecutions = ref<ToolExecution[]>([])

// Inspect drawer state
const activePayload = ref<any>(null)
const payloadTitle = ref('')
const isDrawerVisible = ref(false)

let autoRefreshInterval: ReturnType<typeof setInterval> | null = null

// Toasts notification system
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
  } catch (err) {
    console.error('Error cargando datos de auditoría:', err)
    errorMsg.value = err instanceof Error ? err.message : 'Error al conectar con la API de auditoría.'
    showToast('Error', 'No se pudo conectar con el servidor.', 'error')
  } finally {
    isLoading.value = false
  }
}

// React to global filters
watch([filterChannel, filterPriority], () => {
  void refreshData()
})

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
    showToast('Ejecución Rejected', 'La ejecución ha sido bloqueada y cancelada.', 'success')
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
  void refreshData()
  onRefresh(refreshData)
  autoRefreshInterval = setInterval(() => {
    void refreshData()
  }, 10000)
})

onUnmounted(() => {
  removeRefresh(refreshData)
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval)
  }
})
</script>

<template>
  <div class="audit-dashboard-content">
    <!-- Error Banner -->
    <ErrorBanner :error="errorMsg" @dismiss="errorMsg = null" />

    <!-- Page Header -->
    <PageHeader
      title="Centro de Gobierno Operativo & Auditoría"
      subtitle="Trazabilidad en tiempo real de decisiones autónomas del motor de IA y control de gobernanza."
    />

    <!-- Loading State -->
    <LoadingState v-if="isLoading" message="Cargando centro de auditoría y gobierno..." />

    <template v-else-if="auditEvents.length > 0 || toolExecutions.length > 0">
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
    </template>

    <!-- Empty State -->
    <div v-else class="empty-state-wrapper">
      <EmptyState message="No hay eventos ni ejecuciones registradas en el log de auditoría." />
    </div>
  </div>

  <!-- Payload drawer -->
  <PayloadDrawer
    :payload="activePayload"
    :title="payloadTitle"
    :visible="isDrawerVisible"
    @close="closeDrawer"
  />
</template>

<style scoped>
.audit-dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}
</style>


<style scoped>
.audit-dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}
</style>
