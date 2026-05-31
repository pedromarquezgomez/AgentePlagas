<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchTechnicians,
  isUnauthorizedError,
  listCalendarVisits,
  type Technician,
  type Visit,
  VISIT_STATUSES,
} from '../services/api'

const emit = defineEmits<{
  open: [visitId: string]
  unauthorized: []
}>()

const visits = ref<Visit[]>([])
const technicians = ref<Technician[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedDate = ref(toDateInput(new Date()))
const viewMode = ref<'day' | 'week'>('week')
const technicianFilter = ref('')
const statusFilter = ref('')

const range = computed(() => {
  const base = parseDateInput(selectedDate.value)
  if (viewMode.value === 'day') {
    return { start: base, end: base }
  }

  const start = new Date(base)
  start.setDate(base.getDate() - ((base.getDay() + 6) % 7))
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return { start, end }
})

const days = computed(() => {
  const result: Date[] = []
  const current = new Date(range.value.start)
  while (current <= range.value.end) {
    result.push(new Date(current))
    current.setDate(current.getDate() + 1)
  }
  return result
})

function toDateInput(date: Date): string {
  const normalized = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  return normalized.toISOString().slice(0, 10)
}

function parseDateInput(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDay(date: Date): string {
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'long',
    day: '2-digit',
    month: 'short',
  }).format(date)
}

function formatTime(value: string | null | undefined): string {
  if (!value) return 'Sin hora'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function technicianName(technicianId: string | null | undefined): string {
  if (!technicianId) return 'Sin técnico'
  return technicians.value.find((technician) => technician.id === technicianId)?.name ?? technicianId
}

function visitsForDay(date: Date): Visit[] {
  const key = toDateInput(date)
  return visits.value.filter((visit) => {
    if (!visit.scheduled_start) return false
    const visitDate = new Date(visit.scheduled_start)
    if (Number.isNaN(visitDate.getTime())) return false
    return toDateInput(visitDate) === key
  })
}

async function loadCalendar(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    const [loadedVisits, loadedTechnicians] = await Promise.all([
      listCalendarVisits({
        start_date: toDateInput(range.value.start),
        end_date: toDateInput(range.value.end),
        technician_id: technicianFilter.value || undefined,
        status: statusFilter.value || undefined,
      }),
      fetchTechnicians({ active: true, limit: 200 }),
    ])
    visits.value = loadedVisits
    technicians.value = loadedTechnicians
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar el calendario'
    visits.value = []
  } finally {
    loading.value = false
  }
}

watch([selectedDate, viewMode, technicianFilter, statusFilter], () => {
  void loadCalendar()
})

onMounted(() => {
  void loadCalendar()
})
</script>

<template>
  <section class="filters" aria-label="Filtros de calendario">
    <label>
      Fecha
      <input v-model="selectedDate" type="date" />
    </label>

    <label>
      Vista
      <select v-model="viewMode">
        <option value="week">Semana</option>
        <option value="day">Día</option>
      </select>
    </label>

    <label>
      Técnico
      <select v-model="technicianFilter">
        <option value="">Todos</option>
        <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
          {{ technician.name }}
        </option>
      </select>
    </label>

    <label>
      Estado
      <select v-model="statusFilter">
        <option value="">Todos</option>
        <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
          {{ status }}
        </option>
      </select>
    </label>

    <button class="secondaryButton" type="button" :disabled="loading" @click="loadCalendar">
      Actualizar
    </button>
  </section>

  <section class="contentBand">
    <div v-if="loading" class="stateMessage">Cargando calendario...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
    <div v-else class="calendarGrid">
      <article v-for="day in days" :key="toDateInput(day)" class="calendarDay">
        <header class="calendarDayHeader">
          <h3>{{ formatDay(day) }}</h3>
          <span class="badge">{{ visitsForDay(day).length }}</span>
        </header>

        <div v-if="visitsForDay(day).length === 0" class="calendarEmpty">
          Sin visitas programadas.
        </div>

        <button
          v-for="visit in visitsForDay(day)"
          :key="visit.id"
          class="calendarVisit"
          type="button"
          @click="emit('open', visit.id)"
        >
          <span class="calendarVisitTime">
            {{ formatTime(visit.scheduled_start) }} - {{ formatTime(visit.scheduled_end) }}
          </span>
          <span class="calendarVisitTitle">Incidencia {{ visit.incident_id }}</span>
          <span>{{ technicianName(visit.technician_id) }}</span>
          <span class="badge status">{{ visit.status }}</span>
        </button>
      </article>
    </div>
  </section>
</template>
