<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useTechnicians } from '../composables/useTechnicians'
import {
  fetchVisits,
  fetchIncidents,
  fetchDocuments,
  updateVisit,
  type Visit,
  type Incident,
  type OperationalDocument,
  type Technician,
} from '../services/api'
import { formatStatus } from '../utils/labels'

import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import TechnicianCard from '../components/dashboard/TechnicianCard.vue'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  technicians,
  loading: loadingTechs,
  error: techsError,
  technicianActiveFilter,
  hasTechnicianFilters,
  loadTechnicians,
  clearTechnicianFilters
} = useTechnicians()

// Datos auxiliares para las tarjetas y drawer
const visits = ref<Visit[]>([])
const incidents = ref<Incident[]>([])
const documents = ref<OperationalDocument[]>([])
const loadingData = ref(false)

const selectedTechnicianId = ref<string | null>(null)

function openNewTechnician() {
  void router.push('/technicians/new')
}

function openVisit(visitId: string) {
  void router.push(`/visits/${encodeURIComponent(visitId)}`)
}

async function loadAllData() {
  loadingData.value = true
  try {
    const [loadedVisits, loadedIncidents, loadedDocs] = await Promise.all([
      fetchVisits({ limit: 500 }),
      fetchIncidents({ limit: 500 }),
      fetchDocuments({ limit: 500 }),
    ])
    visits.value = loadedVisits
    incidents.value = loadedIncidents
    documents.value = loadedDocs
  } catch (err) {
    console.error('Error cargando datos de técnicos auxiliares:', err)
  } finally {
    loadingData.value = false
  }
}

async function refreshAll() {
  await Promise.all([
    loadTechnicians(),
    loadAllData()
  ])
}

onMounted(() => {
  void refreshAll()
  onRefresh(refreshAll)
})

onUnmounted(() => {
  removeRefresh(refreshAll)
})

// --- Cálculos por Técnico ---
const todayStr = computed(() => {
  const now = new Date()
  const normalized = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return normalized.toISOString().slice(0, 10)
})

// Mapeamos visitas del técnico para hoy
const techTodayVisitsMap = computed(() => {
  const map: Record<string, Visit[]> = {}
  
  visits.value.forEach(v => {
    if (!v.technician_id || !v.scheduled_start) return
    const vDateStr = v.scheduled_start.slice(0, 10)
    if (vDateStr === todayStr.value) {
      if (!map[v.technician_id]) map[v.technician_id] = []
      map[v.technician_id].push(v)
    }
  })

  // Ordenar cronológicamente
  Object.keys(map).forEach(techId => {
    map[techId].sort((a, b) => {
      const timeA = a.scheduled_start ? new Date(a.scheduled_start).getTime() : 0
      const timeB = b.scheduled_start ? new Date(b.scheduled_start).getTime() : 0
      return timeA - timeB
    })
  })

  return map
})

// Mapeamos total de visitas e incidencias urgentes hoy
const techStatsMap = computed(() => {
  const map: Record<string, { visitsCount: number; urgentsCount: number; nextTime: string | null }> = {}
  
  technicians.value.forEach(t => {
    const todayList = techTodayVisitsMap.value[t.id] || []
    
    // Contar urgentes
    let urgentCount = 0
    todayList.forEach(v => {
      // Buscar incidente
      const inc = incidents.value.find(i => i.id === v.incident_id)
      if (inc) {
        const prio = (inc.operational_priority || inc.priority || '').toLowerCase()
        if (prio === 'urgent' || prio === 'high' || prio === 'urgente' || prio === 'alta') {
          urgentCount++
        }
      }
    })

    // Calcular próxima visita
    let nextTimeStr: string | null = null
    const futureTodayList = todayList.filter(v => {
      if (!v.scheduled_start) return false
      // Filtramos visitas futuras hoy
      return new Date(v.scheduled_start).getTime() > Date.now() && v.status !== 'completed' && v.status !== 'cancelled'
    })
    
    if (futureTodayList.length > 0) {
      const date = new Date(futureTodayList[0].scheduled_start!)
      nextTimeStr = new Intl.DateTimeFormat('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
      }).format(date)
    }

    map[t.id] = {
      visitsCount: todayList.length,
      urgentsCount: urgentCount,
      nextTime: nextTimeStr,
    }
  })

  return map
})

// --- Drawer Técnico Seleccionado ---
const selectedTech = computed(() => {
  return technicians.value.find(t => t.id === selectedTechnicianId.value) || null
})

const selectedTechTodayVisits = computed(() => {
  if (!selectedTechnicianId.value) return []
  return techTodayVisitsMap.value[selectedTechnicianId.value] || []
})

const selectedTechAllVisits = computed(() => {
  if (!selectedTechnicianId.value) return []
  return visits.value.filter(v => v.technician_id === selectedTechnicianId.value)
})

const selectedTechIncidents = computed(() => {
  if (!selectedTechnicianId.value) return []
  // Sacamos los IDs de incidentes de sus visitas
  const incidentIds = new Set(selectedTechAllVisits.value.map(v => v.incident_id))
  // Filtramos incidencias activas (no completadas/cerradas/canceladas)
  const closedStatuses = ['completed', 'closed', 'cancelled']
  return incidents.value.filter(i => incidentIds.has(i.id) && !closedStatuses.includes(i.status))
})

const selectedTechDraftDocs = computed(() => {
  if (!selectedTechnicianId.value) return []
  // Sacamos los IDs de sus visitas
  const visitIds = new Set(selectedTechAllVisits.value.map(v => v.id))
  return documents.value.filter(d => d.visit_id && visitIds.has(d.visit_id) && d.status === 'draft')
})

function closeDrawer() {
  selectedTechnicianId.value = null
}

function selectTechnician(id: string) {
  selectedTechnicianId.value = id
}

function viewTechnicianDetail(id: string) {
  void router.push(`/technicians/${encodeURIComponent(id)}`)
}

function formatTime(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatDateOnly(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
  }).format(date)
}
</script>

<template>
  <div class="technicians-page">
    <div class="sectionHeader">
      <PageHeader
        title="Técnicos de Servicio"
        subtitle="Listado y estado de disponibilidad del personal técnico asignado."
      />
      <button class="primaryButton" type="button" @click="openNewTechnician">
        Nuevo técnico
      </button>
    </div>

    <!-- Filtros -->
    <section class="filters" aria-label="Filtros de técnicos">
      <label>
        Estado Activo
        <select v-model="technicianActiveFilter" @change="loadTechnicians">
          <option value="">Todos los técnicos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasTechnicianFilters" @click="clearTechnicianFilters">
        Limpiar Filtros
      </button>
    </section>

    <!-- Contenido Principal -->
    <section class="contentBand">
      <LoadingState v-if="loadingTechs || loadingData" message="Cargando panel de técnicos..." />
      <ErrorBanner v-else-if="techsError" :error="techsError" @dismiss="techsError = null" />
      
      <!-- Empty State Inteligente -->
      <div v-else-if="technicians.length === 0" class="empty-techs-container">
        <EmptyState message="No existen técnicos" />
        <div class="stateAction">
          <button class="primaryButton" type="button" @click="openNewTechnician">
            Crear Técnico
          </button>
        </div>
      </div>

      <!-- Grid de Tarjetas -->
      <div v-else class="techs-grid">
        <TechnicianCard
          v-for="tech in technicians"
          :key="tech.id"
          :technician="tech"
          :visitsCount="techStatsMap[tech.id]?.visitsCount || 0"
          :urgentsCount="techStatsMap[tech.id]?.urgentsCount || 0"
          :nextVisitTime="techStatsMap[tech.id]?.nextTime"
          @select="selectTechnician"
        />
      </div>
    </section>

    <!-- Drawer Lateral de Detalle del Técnico -->
    <div class="drawer-overlay" v-if="selectedTech" @click="closeDrawer">
      <div class="drawer-panel" @click.stop>
        <header class="drawer-header">
          <div class="drawer-header-meta">
            <span class="avatar-large">{{ selectedTech.name.slice(0, 2).toUpperCase() }}</span>
            <div>
              <h2>{{ selectedTech.name }}</h2>
              <span class="badge status">{{ selectedTech.active ? 'ACTIVO' : 'INACTIVO' }}</span>
            </div>
          </div>
          <button class="close-btn" type="button" @click="closeDrawer">✕</button>
        </header>

        <div class="drawer-body">
          <!-- Sección de contacto -->
          <div class="info-section">
            <h3>Contacto</h3>
            <p><strong>Teléfono:</strong> {{ selectedTech.phone || 'Sin teléfono' }}</p>
            <p><strong>Email:</strong> {{ selectedTech.email || 'Sin email' }}</p>
            <p><strong>Área de Servicio:</strong> 📍 {{ selectedTech.service_area || 'Sin zona' }}</p>
          </div>

          <!-- Agenda de hoy -->
          <div class="info-section">
            <h3>Calendario de Hoy</h3>
            <div v-if="selectedTechTodayVisits.length === 0" class="drawer-empty-msg">
              Sin visitas programadas para hoy.
            </div>
            <div class="mini-list" v-else>
              <div 
                v-for="v in selectedTechTodayVisits" 
                :key="v.id" 
                class="mini-item"
                @click="openVisit(v.id)"
              >
                <span class="time-tag">{{ formatTime(v.scheduled_start) }}</span>
                <div class="mini-content">
                  <span class="mini-title">Incidencia {{ v.incident_id.slice(0, 6) }}</span>
                  <span class="mini-desc">{{ v.address || 'Sin dirección' }}</span>
                </div>
                <span class="badge status">{{ formatStatus(v.status) }}</span>
              </div>
            </div>
          </div>

          <!-- Visitas asignadas -->
          <div class="info-section">
            <h3>Visitas Asignadas ({{ selectedTechAllVisits.length }})</h3>
            <div v-if="selectedTechAllVisits.length === 0" class="drawer-empty-msg">
              Sin visitas asignadas.
            </div>
            <div class="mini-list" v-else>
              <div
                v-for="v in selectedTechAllVisits"
                :key="v.id"
                class="mini-item"
                @click="openVisit(v.id)"
              >
                <span class="time-tag">🗓️ {{ formatDateOnly(v.scheduled_start) }} {{ formatTime(v.scheduled_start) }}</span>
                <div class="mini-content">
                  <span class="mini-title">Incidencia {{ v.incident_id.slice(0, 6) }}</span>
                  <span class="mini-desc">{{ v.address || 'Sin dirección' }}</span>
                </div>
                <span class="badge status">{{ formatStatus(v.status) }}</span>
              </div>
            </div>
          </div>

          <!-- Incidencias abiertas -->
          <div class="info-section">
            <h3>Incidencias Abiertas ({{ selectedTechIncidents.length }})</h3>
            <div v-if="selectedTechIncidents.length === 0" class="drawer-empty-msg">
              No tiene incidencias abiertas asignadas.
            </div>
            <div class="mini-list" v-else>
              <div 
                v-for="i in selectedTechIncidents" 
                :key="i.id" 
                class="mini-item"
                @click="router.push(`/incidents/${i.id}`)"
              >
                <div class="mini-content">
                  <span class="mini-title">{{ i.location || 'Localización S/D' }}</span>
                  <span class="mini-desc">{{ i.pest_type || 'Plaga S/D' }}</span>
                </div>
                <span class="badge" :class="`priority-${i.priority}`">{{ i.priority }}</span>
              </div>
            </div>
          </div>

          <!-- Documentos pendientes -->
          <div class="info-section">
            <h3>Documentos Pendientes (Borrador)</h3>
            <div v-if="selectedTechDraftDocs.length === 0" class="drawer-empty-msg">
              Sin documentos pendientes de revisión.
            </div>
            <div class="mini-list" v-else>
              <div 
                v-for="d in selectedTechDraftDocs" 
                :key="d.id" 
                class="mini-item"
                @click="router.push(`/documents/${d.id}`)"
              >
                <div class="mini-content">
                  <span class="mini-title">{{ d.title }}</span>
                  <span class="mini-desc">Visita: {{ d.visit_id?.slice(0, 6) }}</span>
                </div>
                <span class="badge status">BORRADOR</span>
              </div>
            </div>
          </div>
        </div>

        <footer class="drawer-footer">
          <button class="primaryButton" type="button" @click="viewTechnicianDetail(selectedTech.id)">
            Editar Perfil Técnico
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
.technicians-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
}

.techs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.empty-techs-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

/* --- Estilos Drawer Lateral Premium --- */
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
  max-width: 460px;
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

.avatar-large {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #27272a;
  color: #34d399;
  font-weight: 900;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-header h2 {
  font-size: 18px;
  font-weight: 800;
  margin: 0 0 4px 0;
  color: #f4f4f5;
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

.info-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-section h3 {
  font-size: 12px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #27272a;
  padding-bottom: 6px;
  margin: 0;
}

.info-section p {
  font-size: 13px;
  color: #d4d4d8;
  margin: 0;
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

.time-tag {
  font-size: 11px;
  font-weight: 800;
  color: #fbbf24;
  white-space: nowrap;
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
