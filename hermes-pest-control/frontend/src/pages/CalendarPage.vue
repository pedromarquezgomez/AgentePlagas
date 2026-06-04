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
      <button class="primaryButton" type="button" @click="scheduleNewVisit">
        Programar Visita
      </button>
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
</style>
