<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useIncidents } from '../composables/useIncidents'
import {
  fetchVisits,
  fetchTechnicians,
  fetchDocuments,
  fetchDecisionRecords,
  listShadowDecisionRecords,
  isUnauthorizedError,
  type Visit,
  type Technician,
  type OperationalDocument,
  type DecisionRecord,
  type ShadowDecisionRecord,
  type Incident,
  INCIDENT_STATUSES,
  OPERATIONAL_PRIORITIES,
  PEST_TYPES,
  DISPATCH_BUCKETS,
  SLA_STATUSES
} from '../services/api'
import {
  formatStatus,
  formatPriority,
  formatPestType,
  formatDispatchBucket,
  formatSlaStatus,
  normalizePestType,
} from '../utils/labels'

import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import IncidentTimeline from '../components/dashboard/IncidentTimeline.vue'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  incidents,
  loading: loadingIncidents,
  error: incidentsError,
  statusFilter,
  priorityFilter,
  pestTypeFilter,
  dispatchBucketFilter,
  slaStatusFilter,
  hasFilters,
  loadIncidents,
  clearFilters,
  sortIncidents
} = useIncidents()

// Datos auxiliares
const visits = ref<Visit[]>([])
const technicians = ref<Technician[]>([])
const documents = ref<OperationalDocument[]>([])
const decisionRecords = ref<DecisionRecord[]>([])
const shadowDecisions = ref<ShadowDecisionRecord[]>([])
const loadingAux = ref(false)

const selectedIncidentId = ref<string | null>(null)

async function loadAuxiliaryData() {
  loadingAux.value = true
  try {
    const [loadedVisits, loadedTechs, loadedDocs, loadedDecs, loadedShadows] = await Promise.all([
      fetchVisits({ limit: 500 }),
      fetchTechnicians({ limit: 200 }),
      fetchDocuments({ limit: 500 }),
      fetchDecisionRecords({ limit: 100 }),
      listShadowDecisionRecords({ limit: 100 }),
    ])
    visits.value = loadedVisits
    technicians.value = loadedTechs
    documents.value = loadedDocs
    decisionRecords.value = loadedDecs
    shadowDecisions.value = loadedShadows
  } catch (err) {
    console.error('Error cargando datos auxiliares en incidencias:', err)
  } finally {
    loadingAux.value = false
  }
}

async function refreshAll() {
  await Promise.all([
    loadIncidents(),
    loadAuxiliaryData()
  ])
}

onMounted(() => {
  void refreshAll()
  onRefresh(refreshAll)
})

onUnmounted(() => {
  removeRefresh(refreshAll)
})

// --- Mapeos Auxiliares en Cliente ---
const techniciansMap = computed(() => {
  const map: Record<string, Technician> = {}
  technicians.value.forEach(t => {
    map[t.id] = t
  })
  return map
})

// Obtener técnico de la visita asignada al incidente
function getTechnicianNameForIncident(incidentId: string): string {
  const incVisits = visits.value.filter(v => v.incident_id === incidentId)
  if (incVisits.length === 0) return 'Sin asignar'
  // Buscamos la última programada o en curso
  const activeVisit = incVisits.find(v => v.status === 'in_progress' || v.status === 'scheduled') || incVisits[0]
  if (!activeVisit.technician_id) return 'Sin asignar'
  return techniciansMap.value[activeVisit.technician_id]?.name || 'Técnico'
}

// --- Drawer de Detalles del Incidente ---
const selectedIncident = computed(() => {
  return incidents.value.find(i => i.id === selectedIncidentId.value) || null
})

const selectedIncidentVisits = computed(() => {
  if (!selectedIncidentId.value) return []
  return visits.value.filter(v => v.incident_id === selectedIncidentId.value)
})

const selectedIncidentDocs = computed(() => {
  if (!selectedIncidentId.value) return []
  const visitIds = new Set(selectedIncidentVisits.value.map(v => v.id))
  return documents.value.filter(d => 
    d.incident_id === selectedIncidentId.value || (d.visit_id && visitIds.has(d.visit_id))
  )
})

const selectedIncidentDecisions = computed(() => {
  if (!selectedIncidentId.value || !selectedIncident.value) return []
  const cId = selectedIncident.value.conversation_id
  return decisionRecords.value.filter(d => 
    d.incident_id === selectedIncidentId.value || (cId && d.conversation_id === cId)
  )
})

const selectedIncidentShadowDecs = computed(() => {
  if (!selectedIncidentId.value || !selectedIncident.value) return []
  const cId = selectedIncident.value.conversation_id
  return shadowDecisions.value.filter(d => cId && d.conversation_id === cId)
})

function openIncidentDrawer(id: string) {
  selectedIncidentId.value = id
}

function closeDrawer() {
  selectedIncidentId.value = null
}

function viewFullDetail(id: string) {
  void router.push(`/incidents/${encodeURIComponent(id)}`)
}

function createNewVisit() {
  if (!selectedIncidentId.value) return
  // Redirigir para crear visita
  void router.push({
    path: '/visits/new',
    query: { incident_id: selectedIncidentId.value }
  })
}

function formatSlaHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return 'S/D'
  return `${hours}h`
}

function getSlaClass(status: string | null | undefined): string {
  if (!status) return 'agreement-neutral'
  const s = status.toLowerCase()
  if (s.includes('breach') || s.includes('incump')) return 'priority-high'
  if (s.includes('risk') || s.includes('riesgo')) return 'priority-medium'
  return 'priority-low'
}
</script>

<template>
  <div class="incidents-page">
    <div class="sectionHeader">
      <PageHeader
        title="Centro de Incidencias"
        subtitle="Monitoreo operativo de casos de plagas, asignaciones de SLAs y control HITL."
      />
    </div>

    <!-- Filtros -->
    <section class="filters" aria-label="Filtros de incidencias">
      <label>
        Estado
        <select v-model="statusFilter" @change="loadIncidents">
          <option value="">Todos los estados</option>
          <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
            {{ formatStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Prioridad
        <select v-model="priorityFilter" @change="loadIncidents">
          <option value="">Todas las prioridades</option>
          <option v-for="priority in OPERATIONAL_PRIORITIES" :key="priority" :value="priority">
            {{ formatPriority(priority) }}
          </option>
        </select>
      </label>

      <label>
        Tipo Plaga
        <select v-model="pestTypeFilter" @change="loadIncidents">
          <option value="">Todas las plagas</option>
          <option v-for="pestType in PEST_TYPES" :key="pestType" :value="pestType">
            {{ formatPestType(pestType) }}
          </option>
        </select>
      </label>

      <label>
        Cola despacho
        <select v-model="dispatchBucketFilter" @change="loadIncidents">
          <option value="">Todas las colas</option>
          <option v-for="bucket in DISPATCH_BUCKETS" :key="bucket" :value="bucket">
            {{ formatDispatchBucket(bucket) }}
          </option>
        </select>
      </label>

      <label>
        Estado SLA
        <select v-model="slaStatusFilter" @change="loadIncidents">
          <option value="">Todos los SLAs</option>
          <option v-for="slaStatus in SLA_STATUSES" :key="slaStatus" :value="slaStatus">
            {{ formatSlaStatus(slaStatus) }}
          </option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasFilters" @click="clearFilters">
        Limpiar Filtros
      </button>
    </section>

    <!-- Tabla Compacta -->
    <section class="contentBand">
      <LoadingState v-if="loadingIncidents || loadingAux" message="Cargando incidencias..." />
      <ErrorBanner v-else-if="incidentsError" :error="incidentsError" @dismiss="incidentsError = null" />
      <EmptyState v-else-if="incidents.length === 0" message="No hay incidencias para los filtros seleccionados." />
      
      <div v-else class="tableShell">
        <table class="incidentTable compact-table">
          <thead>
            <tr>
              <th>Cliente / Ubicación</th>
              <th>Plaga</th>
              <th>Prioridad</th>
              <th>SLA</th>
              <th>Técnico Asignado</th>
              <th>Estado</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="inc in incidents" 
              :key="inc.id" 
              class="incident-row"
              @click="openIncidentDrawer(inc.id)"
            >
              <td class="client-cell">
                <span class="client-name">{{ inc.location || 'Localización S/D' }}</span>
                <span class="affected-area" v-if="inc.affected_area">{{ inc.affected_area }}</span>
              </td>
              <td>
                <span class="pest-badge">{{ formatPestType(normalizePestType(inc.pest_type)).toUpperCase() }}</span>
              </td>
              <td>
                <span class="badge" :class="`priority-${inc.priority}`">
                  {{ formatPriority(inc.priority) }}
                </span>
              </td>
              <td>
                <span class="badge" :class="getSlaClass(inc.sla_status)">
                  {{ formatSlaStatus(inc.sla_status) }} ({{ formatSlaHours(inc.remaining_hours) }})
                </span>
              </td>
              <td class="tech-cell">
                👤 {{ getTechnicianNameForIncident(inc.id) }}
              </td>
              <td>
                <span class="badge status">{{ formatStatus(inc.status) }}</span>
              </td>
              <td @click.stop>
                <button class="linkButton" type="button" @click="openIncidentDrawer(inc.id)">
                  Abrir
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Drawer Lateral Derecho del Incidente -->
    <div class="drawer-overlay" v-if="selectedIncident" @click="closeDrawer">
      <div class="drawer-panel" @click.stop>
        <header class="drawer-header">
          <div class="drawer-header-meta">
            <span class="pest-icon-large">🚨</span>
            <div>
              <h2>Incidencia #{{ selectedIncident.id.slice(0, 8).toUpperCase() }}</h2>
              <p class="drawer-subtitle">{{ selectedIncident.location || 'Localización S/D' }}</p>
            </div>
          </div>
          <button class="close-btn" type="button" @click="closeDrawer">✕</button>
        </header>

        <div class="drawer-body">
          <!-- Resumen IA -->
          <div class="drawer-section border-highlight">
            <h3>Resumen Inteligente (IA Hermes)</h3>
            <div class="ai-summary-card">
              <p class="ai-text"><strong>Análisis:</strong> {{ selectedIncident.summary || 'Generando resumen...' }}</p>
              <p class="ai-reason" v-if="selectedIncident.assessment_reason">
                <strong>Razón de la clasificación:</strong> {{ selectedIncident.assessment_reason }}
              </p>
            </div>
          </div>

          <!-- Cronología Unificada -->
          <div class="drawer-section">
            <h3>Línea de Tiempo Operativa</h3>
            <IncidentTimeline 
              :incidentId="selectedIncident.id" 
              :conversationId="selectedIncident.conversation_id"
            />
          </div>

          <!-- Visitas Técnicas -->
          <div class="drawer-section">
            <div class="section-title-row">
              <h3>Visitas del Servicio ({{ selectedIncidentVisits.length }})</h3>
              <button class="linkButton create-visit-shortcut" type="button" @click="createNewVisit">
                + Programar Visita
              </button>
            </div>
            
            <div v-if="selectedIncidentVisits.length === 0" class="drawer-empty-msg">
              Sin visitas programadas aún.
            </div>
            <div class="mini-list" v-else>
              <div 
                v-for="v in selectedIncidentVisits" 
                :key="v.id" 
                class="mini-item"
                @click="router.push(`/visits/${v.id}`)"
              >
                <div class="mini-content">
                  <span class="mini-title">🗓️ {{ formatStatus(v.status).toUpperCase() }}</span>
                  <span class="mini-desc">Técnico: {{ techniciansMap[v.technician_id ?? '']?.name || 'Sin asignar' }}</span>
                </div>
                <span class="badge status">Ver detalles</span>
              </div>
            </div>
          </div>

          <!-- Documentos Generados -->
          <div class="drawer-section">
            <h3>Reportes y Documentos ({{ selectedIncidentDocs.length }})</h3>
            <div v-if="selectedIncidentDocs.length === 0" class="drawer-empty-msg">
              No se han generado reportes operativos.
            </div>
            <div class="mini-list" v-else>
              <div 
                v-for="d in selectedIncidentDocs" 
                :key="d.id" 
                class="mini-item"
                @click="router.push(`/documents/${d.id}`)"
              >
                <div class="mini-content">
                  <span class="mini-title">📄 {{ d.title }}</span>
                  <span class="mini-desc">Estado: {{ formatStatus(d.status) }}</span>
                </div>
                <span class="badge status">Ver</span>
              </div>
            </div>
          </div>

          <!-- Auditoría de Decisiones IA -->
          <div class="drawer-section">
            <h3>Auditoría de Decisiones IA</h3>
            <div v-if="selectedIncidentDecisions.length === 0" class="drawer-empty-msg">
              Sin registros de auditoría de decisión.
            </div>
            <div class="audit-list" v-else>
              <div 
                v-for="dec in selectedIncidentDecisions" 
                :key="dec.id"
                class="audit-item"
              >
                <p><strong>Acción IA:</strong> {{ dec.action_type }}</p>
                <p><strong>Canal:</strong> {{ dec.channel.toUpperCase() }} | <strong>Fallback:</strong> {{ dec.fallback_used ? 'Sí ⚠️' : 'No' }}</p>
                <p class="audit-date" v-if="dec.created_at">⏱️ {{ new Date(dec.created_at).toLocaleString('es-ES') }}</p>
              </div>
            </div>
          </div>

          <!-- Conversación de Origen -->
          <div class="drawer-section">
            <h3>Canal de Conversación</h3>
            <div class="conversation-info">
              <p><strong>ID de Conversación:</strong> <code>{{ selectedIncident.conversation_id || 'S/D' }}</code></p>
              <p><strong>Canal de intake:</strong> 📱 {{ selectedIncident.channel.toUpperCase() }}</p>
              <p v-if="selectedIncident.created_at">
                <strong>Fecha Entrada:</strong> {{ new Date(selectedIncident.created_at).toLocaleString('es-ES') }}
              </p>
            </div>
          </div>
        </div>

        <footer class="drawer-footer">
          <button class="primaryButton" type="button" @click="viewFullDetail(selectedIncident.id)">
            Ir al Detalle Completo
          </button>
          <button class="secondaryButton" type="button" @click="closeDrawer">
            Cerrar
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.incidents-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
}

.compact-table {
  min-width: 1000px;
}

.incident-row {
  cursor: pointer;
}

.client-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.client-name {
  font-weight: 800;
  color: #f4f4f5;
}

.affected-area {
  font-size: 11px;
  color: #71717a;
  font-weight: 600;
}

.pest-badge {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}

.tech-cell {
  color: #d4d4d8;
  font-weight: 700;
  font-size: 13px;
}

/* --- Estilos Drawer Lateral Incidente --- */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 100%;
  max-width: 520px;
  background: #141416;
  border-left: 1px solid #27272a;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.drawer-header {
  padding: 24px;
  border-bottom: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-header-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.pest-icon-large {
  font-size: 32px;
  background: #27272a;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-header h2 {
  font-size: 18px;
  font-weight: 900;
  margin: 0 0 2px 0;
  color: #f4f4f5;
}

.drawer-subtitle {
  color: #71717a;
  font-size: 13px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: 0;
  color: #71717a;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
}

.close-btn:hover {
  color: #f4f4f5;
}

.drawer-body {
  padding: 24px;
  overflow-y: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.drawer-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.drawer-section h3 {
  font-size: 12px;
  font-weight: 900;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #27272a;
  padding-bottom: 6px;
  margin: 0;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.create-visit-shortcut {
  font-size: 11px;
}

.border-highlight {
  border-left: 3px solid #10b981;
  padding-left: 12px;
}

.ai-summary-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-text {
  font-size: 13px;
  color: #e4e4e7;
  line-height: 1.5;
  margin: 0;
}

.ai-reason {
  font-size: 11px;
  color: #a1a1aa;
  margin: 0;
  line-height: 1.4;
  border-top: 1px solid #27272a;
  padding-top: 8px;
  font-style: italic;
}

.drawer-empty-msg {
  color: #52525b;
  font-size: 12px;
  font-weight: 600;
  padding: 12px;
  border: 1px dashed rgba(39, 39, 42, 0.4);
  border-radius: 6px;
  text-align: center;
}

.mini-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mini-item {
  background: #1c1c1f;
  border: 1px solid #27272a;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.mini-item:hover {
  border-color: #3f3f46;
  background: #27272a;
}

.mini-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-grow: 1;
  min-width: 0;
}

.mini-title {
  font-size: 12px;
  font-weight: 750;
  color: #f4f4f5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-desc {
  font-size: 10px;
  color: #71717a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audit-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.audit-item {
  background: #09090b;
  border: 1px solid #27272a;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 11px;
}

.audit-item p {
  margin: 0 0 4px 0;
  color: #a1a1aa;
}

.audit-item p strong {
  color: #d4d4d8;
}

.audit-item p:last-child {
  margin-bottom: 0;
}

.audit-date {
  color: #52525b !important;
  font-weight: 600;
}

.conversation-info {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
}

.conversation-info p {
  margin: 0 0 6px 0;
  color: #a1a1aa;
}

.conversation-info p strong {
  color: #d4d4d8;
}

.conversation-info p:last-child {
  margin-bottom: 0;
}

.drawer-footer {
  padding: 24px;
  border-top: 1px solid #27272a;
  display: flex;
  gap: 12px;
}

.drawer-footer button {
  flex-grow: 1;
}
</style>
