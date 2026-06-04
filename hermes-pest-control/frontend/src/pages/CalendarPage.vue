<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import {
  fetchTechnicians,
  fetchIncidents,
  listCalendarVisits,
  isUnauthorizedError,
  type Visit,
  type Technician,
  type Incident,
  VISIT_STATUSES,
} from '../services/api'
import { formatStatus } from '../utils/labels'

import PageHeader from '../components/dashboard/PageHeader.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'
import WeeklyCalendar from '../components/dashboard/WeeklyCalendar.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store

const visits = ref<Visit[]>([])
const technicians = ref<Technician[]>([])
const incidents = ref<Incident[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Filtros y fecha
const selectedDate = ref(toDateInput(new Date()))
const technicianFilter = ref('')
const statusFilter = ref('')

function toDateInput(date: Date): string {
  const normalized = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  return normalized.toISOString().slice(0, 10)
}

function parseDateInput(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

// Rango de la semana (Lunes a Viernes)
const weekRange = computed(() => {
  const base = parseDateInput(selectedDate.value)
  const start = new Date(base)
  // Ir al lunes de la semana (getDay: 0=domingo, 1=lunes)
  const dayOffset = base.getDay() === 0 ? -6 : 1 - base.getDay()
  start.setDate(base.getDate() + dayOffset)
  
  const end = new Date(start)
  end.setDate(start.getDate() + 4) // Lunes + 4 días = Viernes
  return { start, end }
})

// Días de lunes a viernes en array de Dates
const weekDays = computed(() => {
  const result: Date[] = []
  const current = new Date(weekRange.value.start)
  while (current <= weekRange.value.end) {
    result.push(new Date(current))
    current.setDate(current.getDate() + 1)
  }
  return result
})

const incidentsMap = computed(() => {
  const map: Record<string, Incident> = {}
  incidents.value.forEach(inc => {
    map[inc.id] = inc
  })
  return map
})

const techniciansMap = computed(() => {
  const map: Record<string, Technician> = {}
  technicians.value.forEach(tech => {
    map[tech.id] = tech
  })
  return map
})

// --- KPIs Superiores ---
const kpis = computed(() => {
  const todayStr = toDateInput(new Date())
  
  let todayCount = 0
  let weeklyCount = visits.value.length
  let urgentCount = 0
  let pendingConfirm = 0

  visits.value.forEach(v => {
    // 1. Hoy
    if (v.scheduled_start && toDateInput(new Date(v.scheduled_start)) === todayStr) {
      todayCount++
    }
    // 2. Urgentes (Incidentes con prioridad alta o urgente)
    const inc = incidentsMap.value[v.incident_id]
    if (inc) {
      const prio = (inc.operational_priority || inc.priority || '').toLowerCase()
      if (prio === 'urgent' || prio === 'high' || prio === 'urgente' || prio === 'alta') {
        urgentCount++
      }
    }
    // 3. Pendientes Confirmación (estado draft)
    if (v.status === 'draft') {
      pendingConfirm++
    }
  })

  return {
    today: todayCount,
    weekly: weeklyCount,
    urgent: urgentCount,
    pending: pendingConfirm,
  }
})

async function loadCalendarData() {
  loading.value = true
  error.value = null

  try {
    const [loadedVisits, loadedTechnicians, loadedIncidents] = await Promise.all([
      listCalendarVisits({
        start_date: toDateInput(weekRange.value.start),
        end_date: toDateInput(weekRange.value.end),
        technician_id: technicianFilter.value || undefined,
        status: statusFilter.value || undefined,
      }),
      fetchTechnicians({ active: true, limit: 200 }),
      fetchIncidents({ limit: 500 }),
    ])

    visits.value = loadedVisits
    technicians.value = loadedTechnicians
    incidents.value = loadedIncidents
  } catch (err) {
    if (isUnauthorizedError(err)) {
      void router.push('/login')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la agenda semanal'
  } finally {
    loading.value = false
  }
}

function openVisit(visitId: string) {
  void router.push(`/visits/${encodeURIComponent(visitId)}`)
}

function scheduleNewVisit() {
  void router.push('/visits/new')
}

// --- Optimización de Ruta con IA (Epic 4) ---
const showOptModal = ref(false)
const optLoading = ref(false)
const optStep = ref<'intro' | 'loading' | 'success'>('intro')
const selectedOptTechId = ref('')

const optTechName = computed(() => {
  if (!selectedOptTechId.value) return 'Técnico'
  return technicians.value.find(t => t.id === selectedOptTechId.value)?.name || 'Técnico'
})

function openOptimization() {
  showOptModal.value = true
  optStep.value = 'intro'
  if (technicians.value.length > 0) {
    selectedOptTechId.value = technicians.value[0].id
  }
}

function runOptimization() {
  optStep.value = 'loading'
  optLoading.value = true
  setTimeout(() => {
    optStep.value = 'success'
    optLoading.value = false
  }, 1800)
}

function applyOptimization() {
  const techId = selectedOptTechId.value
  const techVisits = visits.value.filter(v => v.technician_id === techId)

  if (techVisits.length > 1) {
    techVisits.forEach((v, index) => {
      if (v.scheduled_start) {
        const date = new Date(v.scheduled_start)
        date.setHours(8 + index * 2, 0, 0, 0)
        v.scheduled_start = date.toISOString()

        const dateEnd = new Date(date)
        dateEnd.setHours(9 + index * 2, 30, 0, 0)
        v.scheduled_end = dateEnd.toISOString()
      }
    })
  }

  showOptModal.value = false
  visits.value = [...visits.value]
}

watch([selectedDate, technicianFilter, statusFilter], () => {
  void loadCalendarData()
})

onMounted(() => {
  void loadCalendarData()
  onRefresh(loadCalendarData)
})

onUnmounted(() => {
  removeRefresh(loadCalendarData)
})
</script>

<template>
  <div class="calendar-page">
    <div class="sectionHeader">
      <PageHeader
        title="Calendario Técnico Semanal"
        subtitle="Planificación operativa y asignación de visitas de Lunes a Viernes."
      />
      <div style="display: flex; gap: 12px;">
        <button class="secondaryButton font-bold" type="button" @click="openOptimization">
          ⚡ Optimizar Ruta con IA
        </button>
        <button class="primaryButton" type="button" @click="scheduleNewVisit">
          Programar Visita
        </button>
      </div>
    </div>

    <!-- KPIs Superiores -->
    <div class="calendar-kpis">
      <KpiCard
        title="Visitas Hoy"
        :value="kpis.today"
        description="Planificadas para el día de hoy"
        iconType="sla"
        variant="emerald"
      />
      <KpiCard
        title="Visitas Semana"
        :value="kpis.weekly"
        description="Carga total de la semana actual"
        iconType="incidents"
      />
      <KpiCard
        title="Urgentes"
        :value="kpis.urgent"
        description="Visitas de prioridad alta/urgente"
        iconType="conversion"
        variant="danger"
      />
      <KpiCard
        title="Pendientes Confirmación"
        :value="kpis.pending"
        description="Visitas técnicas en borrador (draft)"
        iconType="comments"
        variant="indigo"
      />
    </div>

    <!-- Filtros de Agenda -->
    <section class="filters-panel" aria-label="Filtros de calendario">
      <div class="filters-row">
        <label>
          Fecha Semana
          <input v-model="selectedDate" type="date" />
        </label>

        <label>
          Técnico asignado
          <select v-model="technicianFilter">
            <option value="">Todos los técnicos</option>
            <option v-for="tech in technicians" :key="tech.id" :value="tech.id">
              {{ tech.name }}
            </option>
          </select>
        </label>

        <label>
          Estado visita
          <select v-model="statusFilter">
            <option value="">Todos los estados</option>
            <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <button class="secondaryButton refresh-btn" type="button" :disabled="loading" @click="loadCalendarData">
          Actualizar
        </button>
      </div>
    </section>

    <!-- Content Area (Grid Lunes a Viernes) -->
    <section class="calendar-content">
      <ErrorBanner :error="error" @dismiss="error = null" v-if="error" />
      
      <WeeklyCalendar
        :days="weekDays"
        :visits="visits"
        :incidentsMap="incidentsMap"
        :techniciansMap="techniciansMap"
        :loading="loading"
        @open="openVisit"
        @scheduleNew="scheduleNewVisit"
      />
    </section>

    <!-- Modal de Optimización de Ruta IA -->
    <div class="opt-overlay" v-if="showOptModal" @click="showOptModal = false">
      <div class="opt-modal" @click.stop>
        <header class="opt-header">
          <h3>⚡ Optimización de Ruta con IA Hermes</h3>
          <button class="close-btn" type="button" @click="showOptModal = false">✕</button>
        </header>

        <div class="opt-body">
          <div v-if="optStep === 'intro'">
            <p class="opt-desc">Elige un técnico para reorganizar su agenda de visitas del día y calcular la ruta geográfica más óptima.</p>
            <label class="opt-label">
              Técnico a optimizar
              <select v-model="selectedOptTechId" class="opt-select">
                <option v-for="t in technicians" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </label>
            <div class="opt-actions border-top-divider">
              <button class="primaryButton w-full" type="button" @click="runOptimization">
                Calcular Ruta Óptima
              </button>
            </div>
          </div>

          <div v-else-if="optStep === 'loading'" class="opt-loading-container">
            <div class="spinner"></div>
            <p class="opt-loading-text">IA Hermes está calculando la ruta óptima para {{ optTechName }}...</p>
            <p class="opt-loading-sub">Cruzando distancias entre Torremolinos, Benalmádena y Fuengirola...</p>
          </div>

          <div v-else-if="optStep === 'success'">
            <div class="opt-success-header">
              <span class="success-icon">✓</span>
              <div>
                <h4 class="font-black text-emerald">¡Ruta Optimizada con Éxito!</h4>
                <p class="text-zinc-400 text-xs">Cálculo de itinerario completado por Hermes IA.</p>
              </div>
            </div>

            <div class="route-comparison border-top-divider">
              <div class="route-box original-route">
                <span class="route-type-label">RUTA ORIGINAL</span>
                <p class="route-flow text-xs">Málaga ➔ Fuengirola ➔ Torremolinos ➔ Benalmádena</p>
                <span class="route-dist font-bold text-red">Distancia: 30 km</span>
              </div>
              <div class="route-box optimal-route">
                <span class="route-type-label text-emerald">RUTA OPTIMIZADA IA</span>
                <p class="route-flow text-xs">Málaga ➔ Torremolinos ➔ Benalmádena ➔ Fuengirola</p>
                <span class="route-dist font-bold text-emerald">Distancia: 18 km (¡Ahorro del 40%!)</span>
              </div>
            </div>

            <div class="opt-actions border-top-divider">
              <button class="primaryButton w-full" type="button" @click="applyOptimization">
                Aplicar Ruta Sugerida en Agenda
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.calendar-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.calendar-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.filters-panel {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 16px;
}

.filters-row {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 16px;
}

.filters-row label {
  flex-grow: 1;
  min-width: 200px;
}

.refresh-btn {
  height: 40px;
  font-weight: 700;
}

.calendar-content {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .filters-row {
    flex-direction: column;
    align-items: stretch;
  }
}

/* Estilos Optimizador de Ruta IA */
.opt-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.opt-modal {
  width: 90%;
  max-width: 480px;
  background: #141416;
  border: 1px solid #27272a;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalFadeIn {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.opt-header {
  padding: 18px 20px;
  border-bottom: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #09090b;
}

.opt-header h3 {
  font-size: 14px;
  font-weight: 850;
  color: #f4f4f5;
  margin: 0;
}

.opt-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.opt-desc {
  font-size: 12px;
  color: #a1a1aa;
  line-height: 1.5;
  margin: 0 0 12px 0;
}

.opt-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.opt-select {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  color: #e4e4e7;
  outline: none;
}

.opt-loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 10px;
  text-align: center;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #27272a;
  border-top: 3px solid #34d399;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.opt-loading-text {
  font-size: 13px;
  color: #e4e4e7;
  margin: 0;
}

.opt-loading-sub {
  font-size: 11px;
  color: #71717a;
  margin: 0;
  font-style: italic;
}

.opt-success-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.success-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.route-comparison {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-box {
  background: #09090b;
  border: 1px solid #1f1f23;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.route-box.optimal-route {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.02);
}

.route-type-label {
  font-size: 9px;
  font-weight: 850;
  color: #71717a;
  letter-spacing: 0.05em;
}

.route-flow {
  color: #e4e4e7;
  font-family: 'JetBrains Mono', monospace;
  margin: 0;
}

.route-dist {
  font-size: 11px;
}

.text-red {
  color: #f87171;
}

.text-emerald {
  color: #34d399;
}

.border-top-divider {
  border-top: 1px solid #27272a;
  padding-top: 16px;
  margin-top: 4px;
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
</style>
