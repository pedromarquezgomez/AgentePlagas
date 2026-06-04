<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import { listIncidents, updateIncident } from '../api/incidents'
import { listToolExecutions, approveToolExecution, rejectToolExecution } from '../api/tools'
import type { Incident, AnalyticsOverview, ToolExecution } from '../api/types'
import { ApiError } from '../api/types'
import KpiCard from '../components/KpiCard.vue'
import OperationalTable from '../components/OperationalTable.vue'
import HumanReviewPanel from '../components/HumanReviewPanel.vue'

const incidents = ref<Incident[]>([])
const metrics = ref<AnalyticsOverview | null>(null)
const proposedTools = ref<ToolExecution[]>([])

const loadingIncidents = ref(false)
const loadingMetrics = ref(false)
const loadingTools = ref(false)
const errorMsg = ref<string | null>(null)

async function fetchMetrics() {
  loadingMetrics.value = true
  try {
    metrics.value = await getAnalyticsOverview()
  } catch (err) {
    console.error('Error cargando métricas en operaciones:', err)
  } finally {
    loadingMetrics.value = false
  }
}

async function fetchIncidents() {
  loadingIncidents.value = true
  try {
    incidents.value = await listIncidents()
  } catch (err) {
    if (err instanceof ApiError) {
      errorMsg.value = `Error al listar incidencias: ${err.message}`
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error al obtener incidencias'
    }
  } finally {
    loadingIncidents.value = false
  }
}

async function fetchTools() {
  loadingTools.value = true
  try {
    proposedTools.value = await listToolExecutions({ review_status: 'proposed' })
  } catch (err) {
    console.error('Error cargando herramientas propuestas:', err)
  } finally {
    loadingTools.value = false
  }
}

async function handleUpdateIncident(id: string, payload: Partial<Incident>) {
  errorMsg.value = null
  try {
    await updateIncident(id, payload)
    await Promise.all([fetchIncidents(), fetchMetrics()])
  } catch (err) {
    if (err instanceof ApiError) {
      alert(`Error al actualizar incidencia: ${err.message}`)
    } else {
      alert(err instanceof Error ? err.message : 'Error inesperado')
    }
  }
}

async function handleApproveTool(id: string) {
  try {
    await approveToolExecution(id)
    await Promise.all([fetchTools(), fetchMetrics()])
  } catch (err) {
    if (err instanceof ApiError) {
      alert(`Error al aprobar: ${err.message}`)
    } else {
      alert(err instanceof Error ? err.message : 'Error inesperado')
    }
  }
}

async function handleRejectTool(id: string) {
  try {
    await rejectToolExecution(id)
    await Promise.all([fetchTools(), fetchMetrics()])
  } catch (err) {
    if (err instanceof ApiError) {
      alert(`Error al rechazar: ${err.message}`)
    } else {
      alert(err instanceof Error ? err.message : 'Error inesperado')
    }
  }
}

async function refreshAll() {
  errorMsg.value = null
  await Promise.all([fetchIncidents(), fetchMetrics(), fetchTools()])
}

onMounted(() => {
  refreshAll()
})
</script>

<template>
  <div class="operations-page">
    <!-- Header -->
    <div class="sectionHeader" style="margin-bottom: 24px;">
      <div>
        <span class="eyebrow">Hermes Pest Control</span>
        <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #17202a;">
          Centro de Operaciones
        </h1>
      </div>
      <button 
        class="primaryButton" 
        type="button" 
        :disabled="loadingIncidents || loadingMetrics || loadingTools" 
        @click="refreshAll"
      >
        {{ (loadingIncidents || loadingMetrics || loadingTools) ? 'Actualizando...' : 'Actualizar Todo' }}
      </button>
    </div>

    <!-- Error Alert -->
    <div 
      v-if="errorMsg" 
      class="errorMessage stateMessage" 
      style="margin-bottom: 24px; padding: 12px 18px; font-size: 14px; border-radius: 8px; border: 1px solid #f1b9aa;"
    >
      ⚠️ {{ errorMsg }}
    </div>

    <!-- KPI Cards Top Bar -->
    <section 
      class="dashboardLayout" 
      style="margin-bottom: 28px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;"
    >
      <KpiCard 
        title="Conversaciones" 
        :value="metrics?.total_conversations ?? '0'" 
        description="Llegadas al sistema"
      />
      <KpiCard 
        title="Incidencias" 
        :value="metrics?.incidents_created ?? '0'" 
        :description="`Canceladas: ${metrics?.cancelled_incidents ?? 0} | Cerradas: ${metrics?.closed_incidents ?? 0}`"
      />
      <KpiCard 
        title="SLA Incumplidos" 
        :value="metrics?.sla_breaches ?? '0'" 
        :variant="(metrics?.sla_breaches ?? 0) > 0 ? 'danger' : 'default'"
        description="Fallas en tiempo límite"
      />
      <KpiCard 
        title="Revisiones de IA" 
        :value="proposedTools.length" 
        :variant="proposedTools.length > 0 ? 'warning' : 'default'"
        description="Propuestas en cola"
      />
    </section>

    <!-- Main Content Area: 2 Columns Layout -->
    <div 
      style="display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 24px; align-items: start;"
      class="detailLayout"
    >
      <!-- Left Column: Incidents Table -->
      <div>
        <div style="margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
          <h2 style="font-size: 18px; font-weight: 800; color: #1e293b; margin: 0;">
            Incidencias de Clientes Activas
          </h2>
          <span style="font-size: 13px; color: #64748b; font-weight: 600;">
            Total: {{ incidents.length }} registradas
          </span>
        </div>
        <OperationalTable 
          :incidents="incidents" 
          :loading="loadingIncidents" 
          @update-incident="handleUpdateIncident"
        />
      </div>

      <!-- Right Column: Human Review Panel -->
      <div>
        <HumanReviewPanel 
          :executions="proposedTools" 
          :loading="loadingTools" 
          @approve="handleApproveTool" 
          @reject="handleRejectTool"
        />
      </div>
    </div>
  </div>
</template>
