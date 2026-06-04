<script setup lang="ts">
import { computed } from 'vue'
import type { Visit, Incident, Technician, VisitStatus } from '../../services/api'
import VisitCard from './VisitCard.vue'

const props = withDefaults(
  defineProps<{
    visits: Visit[]
    incidentsMap: Record<string, Incident>
    techniciansMap: Record<string, Technician>
    allTechnicians: Technician[]
    loading?: boolean
  }>(),
  {
    loading: false,
  }
)

const emit = defineEmits<{
  open: [visitId: string]
  updateStatus: [visitId: string, status: VisitStatus]
  updateTechnician: [visitId: string, technicianId: string | null]
  createVisit: []
}>()

// Agrupador para las 3 columnas
const scheduledVisits = computed(() => {
  return props.visits.filter(v => v.status === 'draft' || v.status === 'scheduled')
})

const inProgressVisits = computed(() => {
  return props.visits.filter(v => v.status === 'in_progress')
})

const completedVisits = computed(() => {
  return props.visits.filter(v => v.status === 'completed')
})

const hasAnyVisits = computed(() => {
  return props.visits.length > 0
})
</script>

<template>
  <div class="visit-kanban-container">
    <div v-if="loading" class="kanban-loading">
      Cargando tablero operativo de visitas...
    </div>

    <template v-else>
      <div v-if="!hasAnyVisits" class="kanban-empty-state">
        <div class="empty-icon">📋</div>
        <h3>No hay visitas programadas</h3>
        <p>No se encontraron registros de visitas técnicas en la base de datos.</p>
        <button class="primaryButton" type="button" @click="emit('createVisit')">
          Crear Visita
        </button>
      </div>

      <div v-else class="kanban-board">
        <!-- PROGRAMADAS -->
        <div class="kanban-column column-scheduled">
          <header class="column-header">
            <span class="column-dot"></span>
            <span class="column-title">PROGRAMADAS</span>
            <span class="column-count">{{ scheduledVisits.length }}</span>
          </header>
          
          <div class="cards-container">
            <div v-if="scheduledVisits.length === 0" class="empty-column-msg">
              Sin visitas programadas
            </div>
            <VisitCard
              v-for="visit in scheduledVisits"
              :key="visit.id"
              :visit="visit"
              :incident="incidentsMap[visit.incident_id]"
              :technicianName="techniciansMap[visit.technician_id ?? '']?.name || 'Sin asignar'"
              :allTechnicians="allTechnicians"
              :show-actions="true"
              @open="visitId => emit('open', visitId)"
              @updateStatus="(visitId, status) => emit('updateStatus', visitId, status)"
              @updateTechnician="(visitId, techId) => emit('updateTechnician', visitId, techId)"
            />
          </div>
        </div>

        <!-- EN CURSO -->
        <div class="kanban-column column-progress">
          <header class="column-header">
            <span class="column-dot"></span>
            <span class="column-title">EN CURSO</span>
            <span class="column-count">{{ inProgressVisits.length }}</span>
          </header>

          <div class="cards-container">
            <div v-if="inProgressVisits.length === 0" class="empty-column-msg">
              Ningún servicio en curso
            </div>
            <VisitCard
              v-for="visit in inProgressVisits"
              :key="visit.id"
              :visit="visit"
              :incident="incidentsMap[visit.incident_id]"
              :technicianName="techniciansMap[visit.technician_id ?? '']?.name || 'Sin asignar'"
              :allTechnicians="allTechnicians"
              :show-actions="true"
              @open="visitId => emit('open', visitId)"
              @updateStatus="(visitId, status) => emit('updateStatus', visitId, status)"
              @updateTechnician="(visitId, techId) => emit('updateTechnician', visitId, techId)"
            />
          </div>
        </div>

        <!-- COMPLETADAS -->
        <div class="kanban-column column-completed">
          <header class="column-header">
            <span class="column-dot"></span>
            <span class="column-title">COMPLETADAS</span>
            <span class="column-count">{{ completedVisits.length }}</span>
          </header>

          <div class="cards-container">
            <div v-if="completedVisits.length === 0" class="empty-column-msg">
              Ningún servicio finalizado
            </div>
            <VisitCard
              v-for="visit in completedVisits"
              :key="visit.id"
              :visit="visit"
              :incident="incidentsMap[visit.incident_id]"
              :technicianName="techniciansMap[visit.technician_id ?? '']?.name || 'Sin asignar'"
              :allTechnicians="allTechnicians"
              :show-actions="true"
              @open="visitId => emit('open', visitId)"
              @updateStatus="(visitId, status) => emit('updateStatus', visitId, status)"
              @updateTechnician="(visitId, techId) => emit('updateTechnician', visitId, techId)"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.visit-kanban-container {
  width: 100%;
}

.kanban-loading {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  color: #a1a1aa;
  padding: 40px;
  text-align: center;
  font-weight: 700;
}

.kanban-empty-state {
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

.kanban-empty-state h3 {
  font-size: 18px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.kanban-empty-state p {
  color: #a1a1aa;
  font-size: 13px;
  margin: 0 0 12px;
  max-width: 320px;
  line-height: 1.5;
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  align-items: start;
}

.kanban-column {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  min-height: 540px;
  display: flex;
  flex-direction: column;
}

.column-header {
  padding: 14px 18px;
  border-bottom: 1px solid #27272a;
  background: #141416;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.column-title {
  color: #f4f4f5;
  font-weight: 900;
  font-size: 12px;
  letter-spacing: 0.05em;
  flex-grow: 1;
}

.column-count {
  background: #27272a;
  color: #a1a1aa;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 9999px;
}

.cards-container {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex-grow: 1;
  overflow-y: auto;
  max-height: 600px;
}

.empty-column-msg {
  color: #52525b;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  padding: 24px 0;
  border: 1px dashed rgba(39, 39, 42, 0.4);
  border-radius: 6px;
}

/* Colores de los dot de las columnas */
.column-scheduled .column-dot { background: #38bdf8; }
.column-progress .column-dot { background: #f59e0b; }
.column-completed .column-dot { background: #10b981; }

@media (max-width: 900px) {
  .kanban-board {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .kanban-column {
    min-height: auto;
  }
}
</style>
