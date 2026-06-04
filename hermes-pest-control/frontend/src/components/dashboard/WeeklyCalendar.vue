<script setup lang="ts">
import { computed } from 'vue'
import type { Visit, Incident, Technician } from '../../services/api'
import VisitCard from './VisitCard.vue'

const props = withDefaults(
  defineProps<{
    days: Date[]
    visits: Visit[]
    incidentsMap: Record<string, Incident>
    techniciansMap: Record<string, Technician>
    loading?: boolean
  }>(),
  {
    loading: false,
  }
)

const emit = defineEmits<{
  open: [visitId: string]
  scheduleNew: []
}>()

function toDateInput(date: Date): string {
  const normalized = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  return normalized.toISOString().slice(0, 10)
}

function formatWeekday(date: Date): string {
  return new Intl.DateTimeFormat('es-ES', { weekday: 'long' }).format(date)
}

function formatDayNumber(date: Date): string {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' }).format(date)
}

// Agrupador de visitas por fecha
const visitsByDay = computed(() => {
  const map: Record<string, Visit[]> = {}
  
  // Inicializar días de lunes a viernes
  props.days.forEach(day => {
    map[toDateInput(day)] = []
  })

  // Agrupar
  props.visits.forEach(visit => {
    if (!visit.scheduled_start) return
    const visitDate = new Date(visit.scheduled_start)
    if (Number.isNaN(visitDate.getTime())) return
    const key = toDateInput(visitDate)
    if (map[key] !== undefined) {
      map[key].push(visit)
    }
  })

  // Ordenar cada día por hora de inicio
  Object.keys(map).forEach(key => {
    map[key].sort((a, b) => {
      const timeA = a.scheduled_start ? new Date(a.scheduled_start).getTime() : 0
      const timeB = b.scheduled_start ? new Date(b.scheduled_start).getTime() : 0
      return timeA - timeB
    })
  })

  return map
})

const hasVisitsInWeek = computed(() => {
  return Object.values(visitsByDay.value).some(list => list.length > 0)
})
</script>

<template>
  <div class="weekly-calendar-container">
    <div v-if="loading" class="calendar-loading">
      Cargando agenda semanal...
    </div>

    <template v-else>
      <div v-if="!hasVisitsInWeek" class="calendar-empty-week">
        <div class="empty-icon">📅</div>
        <h3>Semana sin actividad</h3>
        <p>No se encontraron visitas programadas de lunes a viernes para esta semana.</p>
        <button class="primaryButton" type="button" @click="emit('scheduleNew')">
          Programar Visita
        </button>
      </div>

      <div v-else class="weekly-grid">
        <div 
          v-for="day in days" 
          :key="toDateInput(day)" 
          class="calendar-column"
        >
          <header class="column-header">
            <span class="day-name">{{ formatWeekday(day) }}</span>
            <span class="day-date">{{ formatDayNumber(day) }}</span>
            <span class="day-count" v-if="visitsByDay[toDateInput(day)]?.length > 0">
              {{ visitsByDay[toDateInput(day)].length }}
            </span>
          </header>

          <div class="visits-stack">
            <div 
              v-if="!visitsByDay[toDateInput(day)] || visitsByDay[toDateInput(day)].length === 0" 
              class="empty-day-message"
            >
              Sin visitas programadas.
            </div>

            <VisitCard
              v-for="visit in visitsByDay[toDateInput(day)]"
              :key="visit.id"
              :visit="visit"
              :incident="incidentsMap[visit.incident_id]"
              :technicianName="techniciansMap[visit.technician_id ?? '']?.name || 'Sin asignar'"
              :show-actions="false"
              @open="emit('open', $event)"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.weekly-calendar-container {
  width: 100%;
}

.calendar-loading {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  color: #a1a1aa;
  padding: 40px;
  text-align: center;
  font-weight: 700;
}

.calendar-empty-week {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 48px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}

.empty-icon {
  font-size: 42px;
}

.calendar-empty-week h3 {
  font-size: 18px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.calendar-empty-week p {
  color: #a1a1aa;
  font-size: 13px;
  margin: 0 0 12px;
  max-width: 320px;
  line-height: 1.5;
}

.weekly-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  align-items: start;
}

.calendar-column {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  min-height: 480px;
  display: flex;
  flex-direction: column;
}

.column-header {
  padding: 14px;
  border-bottom: 1px solid #27272a;
  background: #141416;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  display: flex;
  flex-direction: column;
  position: relative;
}

.day-name {
  color: #e4e4e7;
  font-weight: 800;
  font-size: 13px;
  text-transform: capitalize;
}

.day-date {
  color: #71717a;
  font-size: 11px;
  font-weight: 600;
  margin-top: 2px;
}

.day-count {
  position: absolute;
  top: 14px;
  right: 14px;
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}

.visits-stack {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-grow: 1;
  overflow-y: auto;
  max-height: 520px;
}

.empty-day-message {
  color: #52525b; /* zinc-600 */
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  padding: 20px 0;
  border: 1px dashed rgba(39, 39, 42, 0.4);
  border-radius: 6px;
}

@media (max-width: 1024px) {
  .weekly-grid {
    grid-template-columns: 1fr;
    gap: 18px;
  }
  
  .calendar-column {
    min-height: auto;
  }
}
</style>
