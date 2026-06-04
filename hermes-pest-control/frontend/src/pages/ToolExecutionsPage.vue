<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useToolExecutions } from '../composables/useToolExecutions'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import ToolExecutionTable from '../components/ToolExecutionTable.vue'
import { TOOL_REVIEW_STATUSES } from '../services/api'
import {
  formatReviewStatus,
  formatToolName,
  formatToolProvider,
  formatToolDecision,
  formatRiskLevel
} from '../utils/labels'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  toolExecutionRecords,
  toolStatusFilter,
  toolNameFilter,
  toolProviderFilter,
  toolDecisionFilter,
  toolRiskFilter,
  toolRequiresApprovalFilter,
  toolLimitFilter,
  loadingTools,
  errorTools,
  hasToolFilters,
  loadToolExecutionRecords,
  clearToolFilters
} = useToolExecutions()

function openToolExecution(id: string) {
  void router.push(`/tools/${encodeURIComponent(id)}`)
}

onMounted(() => {
  void loadToolExecutionRecords()
  onRefresh(loadToolExecutionRecords)
})

onUnmounted(() => {
  removeRefresh(loadToolExecutionRecords)
})
</script>

<template>
  <div class="tool-executions-page">
    <PageHeader
      title="Acciones de la IA"
      subtitle="Registro y revisión de propuestas de ejecución de herramientas invocadas por el agente de IA."
    />

    <section class="contentBand">
      <div class="infoPanel" aria-label="Explicación de acciones IA">
        Esta pantalla muestra propuestas de herramientas hechas por el agente. Se pueden revisar y aprobar,
        pero en esta fase ninguna aprobación ejecuta Gmail, Calendar, Telegram, WhatsApp ni Firestore.
      </div>
    </section>

    <section class="filters" aria-label="Filtros de acciones IA">
      <label>
        Estado revisión
        <select v-model="toolStatusFilter" @change="loadToolExecutionRecords">
          <option value="">Todos</option>
          <option v-for="status in TOOL_REVIEW_STATUSES" :key="status" :value="status">
            {{ formatReviewStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Herramienta
        <select v-model="toolNameFilter" @change="loadToolExecutionRecords">
          <option value="">Todas</option>
          <option value="incident.propose_incident">{{ formatToolName('incident.propose_incident') }}</option>
          <option value="calendar.propose_event">{{ formatToolName('calendar.propose_event') }}</option>
          <option value="gmail.create_draft">{{ formatToolName('gmail.create_draft') }}</option>
          <option value="telegram.draft_message">{{ formatToolName('telegram.draft_message') }}</option>
          <option value="whatsapp.draft_message">{{ formatToolName('whatsapp.draft_message') }}</option>
        </select>
      </label>

      <label>
        Proveedor
        <select v-model="toolProviderFilter" @change="loadToolExecutionRecords">
          <option value="">Todos</option>
          <option value="incident_service">{{ formatToolProvider('incident_service') }}</option>
          <option value="calendar">{{ formatToolProvider('calendar') }}</option>
          <option value="gmail">{{ formatToolProvider('gmail') }}</option>
          <option value="telegram">{{ formatToolProvider('telegram') }}</option>
          <option value="whatsapp">{{ formatToolProvider('whatsapp') }}</option>
        </select>
      </label>

      <label>
        Decisión
        <select v-model="toolDecisionFilter" @change="loadToolExecutionRecords">
          <option value="">Todas</option>
          <option value="allow">{{ formatToolDecision('allow') }}</option>
          <option value="deny">{{ formatToolDecision('deny') }}</option>
          <option value="require_human_approval">{{ formatToolDecision('require_human_approval') }}</option>
          <option value="convert_to_draft">{{ formatToolDecision('convert_to_draft') }}</option>
          <option value="require_more_data">{{ formatToolDecision('require_more_data') }}</option>
        </select>
      </label>

      <label>
        Riesgo
        <select v-model="toolRiskFilter" @change="loadToolExecutionRecords">
          <option value="">Todos</option>
          <option v-for="risk in [0, 1, 2, 3, 4, 5]" :key="risk" :value="String(risk)">
            {{ formatRiskLevel(risk) }}
          </option>
        </select>
      </label>

      <label>
        Aprobación
        <select v-model="toolRequiresApprovalFilter" @change="loadToolExecutionRecords">
          <option value="">Todas</option>
          <option value="true">Requiere aprobación</option>
          <option value="false">No requiere aprobación</option>
        </select>
      </label>

      <label>
        Límite
        <select v-model="toolLimitFilter" @change="loadToolExecutionRecords">
          <option value="25">25</option>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="200">200</option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasToolFilters" @click="clearToolFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loadingTools" message="Cargando acciones IA..." />
      <ErrorBanner v-else-if="errorTools" :error="errorTools" @dismiss="errorTools = null" />
      <EmptyState v-else-if="toolExecutionRecords.length === 0" message="No hay acciones IA para los filtros seleccionados." />
      <ToolExecutionTable
        v-else
        :records="toolExecutionRecords"
        @open="openToolExecution"
      />
    </section>
  </div>
</template>

<style scoped>
.tool-executions-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
