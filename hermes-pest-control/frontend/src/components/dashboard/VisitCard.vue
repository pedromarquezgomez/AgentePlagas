<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Visit, Incident, Technician, VisitStatus } from '../../services/api'
import { formatStatus } from '../../utils/labels'

const props = withDefaults(
  defineProps<{
    visit: Visit
    incident?: Incident | null
    technicianName?: string
    allTechnicians?: Technician[]
    showActions?: boolean
  }>(),
  {
    incident: null,
    technicianName: 'Sin asignar',
    allTechnicians: () => [],
    showActions: false,
  }
)

const emit = defineEmits<{
  open: [visitId: string]
  updateStatus: [visitId: string, status: VisitStatus]
  updateTechnician: [visitId: string, technicianId: string | null]
}>()

const showReassignDropdown = ref(false)

function formatTime(value: string | null | undefined): string {
  if (!value) return '--:--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value.slice(11, 16)
  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const visitTimeRange = computed(() => {
  const start = formatTime(props.visit.scheduled_start)
  const end = formatTime(props.visit.scheduled_end)
  return `${start} - ${end}`
})

const clientName = computed(() => {
  // Mapeamos cliente a partir de la dirección o de la incidencia
  if (props.visit.address && props.visit.address.trim()) {
    return props.visit.address.split(',')[0].toUpperCase()
  }
  if (props.incident?.location) {
    return props.incident.location.toUpperCase()
  }
  return `INCIDENCIA #${props.visit.incident_id.slice(0, 6).toUpperCase()}`
})

const pestName = computed(() => {
  if (props.incident?.pest_type) {
    const p = props.incident.pest_type.toLowerCase()
    if (p.includes('cockroach') || p.includes('cuca')) return 'Cucarachas 🪳'
    if (p.includes('rodent') || p.includes('roed') || p.includes('rat')) return 'Roedores 🐀'
    if (p.includes('ant') || p.includes('horm')) return 'Hormigas 🐜'
    if (p.includes('fly') || p.includes('vola')) return 'Insectos Voladores 🪰'
    return props.incident.pest_type.toUpperCase()
  }
  return 'Tratamiento General 🧪'
})

const statusClass = computed(() => {
  const s = props.visit.status
  if (s === 'completed') return 'status-completed'
  if (s === 'in_progress') return 'status-progress'
  if (s === 'cancelled') return 'status-cancelled'
  if (s === 'scheduled') return 'status-scheduled'
  return 'status-draft'
})

function changeStatus(newStatus: VisitStatus) {
  emit('updateStatus', props.visit.id, newStatus)
}

function selectTechnician(techId: string) {
  emit('updateTechnician', props.visit.id, techId || null)
  showReassignDropdown.value = false
}
</script>

<template>
  <div class="visit-card" :class="statusClass">
    <div class="visit-header">
      <span class="visit-client">{{ clientName }}</span>
      <span class="status-badge">{{ formatStatus(visit.status).toUpperCase() }}</span>
    </div>

    <div class="visit-details">
      <div class="detail-row">
        <span class="detail-label">Plaga</span>
        <span class="detail-value text-highlight">{{ pestName }}</span>
      </div>
      <div class="detail-row" v-if="incident?.location">
        <span class="detail-label">Localidad</span>
        <span class="detail-value">{{ incident.location }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Técnico</span>
        <span class="detail-value">{{ technicianName }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Hora</span>
        <span class="detail-value time-highlight">⏰ {{ visitTimeRange }}</span>
      </div>
    </div>

    <!-- Actions block -->
    <div class="visit-actions" v-if="showActions">
      <button class="action-btn text-emerald" type="button" @click="emit('open', visit.id)">
        Abrir
      </button>

      <div class="reassign-container">
        <button class="action-btn text-indigo" type="button" @click="showReassignDropdown = !showReassignDropdown">
          Reasignar
        </button>
        <div class="reassign-dropdown" v-if="showReassignDropdown">
          <div class="dropdown-header">Asignar Técnico</div>
          <button
            class="dropdown-item"
            type="button"
            v-for="tech in allTechnicians"
            :key="tech.id"
            @click="selectTechnician(tech.id)"
          >
            {{ tech.name }}
          </button>
          <button class="dropdown-item text-danger" type="button" @click="selectTechnician('')">
            Desasignar
          </button>
        </div>
      </div>

      <button
        class="action-btn text-amber"
        type="button"
        v-if="visit.status !== 'in_progress' && visit.status !== 'completed' && visit.status !== 'cancelled'"
        @click="changeStatus('in_progress')"
      >
        Iniciar
      </button>

      <button
        class="action-btn text-emerald"
        type="button"
        v-if="visit.status === 'in_progress'"
        @click="changeStatus('completed')"
      >
        Finalizar
      </button>

      <button
        class="action-btn text-red"
        type="button"
        v-if="visit.status !== 'completed' && visit.status !== 'cancelled'"
        @click="changeStatus('cancelled')"
      >
        Cancelar
      </button>
    </div>
  </div>
</template>

<style scoped>
.visit-card {
  background: #1c1c1f; /* zinc-900 claro */
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
  min-width: 220px;
}

.visit-card:hover {
  border-color: #3f3f46;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.visit-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.visit-client {
  font-weight: 800;
  font-size: 13px;
  color: #f4f4f5;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}

.status-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
}

/* Colores de bordes izquierdo e indicador en base al estado */
.visit-card.status-draft { border-left: 3px solid #71717a; }
.visit-card.status-draft .status-badge { background: rgba(113, 113, 122, 0.15); color: #a1a1aa; }

.visit-card.status-scheduled { border-left: 3px solid #38bdf8; }
.visit-card.status-scheduled .status-badge { background: rgba(14, 165, 233, 0.15); color: #38bdf8; }

.visit-card.status-progress { border-left: 3px solid #f59e0b; }
.visit-card.status-progress .status-badge { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.visit-card.status-completed { border-left: 3px solid #10b981; }
.visit-card.status-completed .status-badge { background: rgba(16, 185, 129, 0.15); color: #34d399; }

.visit-card.status-cancelled { border-left: 3px solid #ef4444; opacity: 0.65; }
.visit-card.status-cancelled .status-badge { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.visit-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  line-height: 1.4;
}

.detail-label {
  color: #71717a;
  font-weight: 500;
}

.detail-value {
  color: #e4e4e7;
  font-weight: 700;
  text-align: right;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-highlight {
  color: #34d399;
}

.time-highlight {
  color: #fbbf24;
}

.visit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #27272a;
}

.action-btn {
  background: transparent;
  border: 0;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 4px;
  text-transform: uppercase;
  transition: opacity 0.2s;
}

.action-btn:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.text-emerald { color: #34d399; }
.text-indigo { color: #818cf8; }
.text-amber { color: #fbbf24; }
.text-red { color: #f87171; }

.reassign-container {
  position: relative;
  display: inline-block;
}

.reassign-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  background: #18181b;
  border: 1px solid #3f3f46;
  border-radius: 6px;
  padding: 6px 0;
  z-index: 50;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  min-width: 150px;
}

.dropdown-header {
  font-size: 9px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  padding: 4px 12px;
  border-bottom: 1px solid #27272a;
  margin-bottom: 4px;
}

.dropdown-item {
  background: transparent;
  border: 0;
  color: #d4d4d8;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  padding: 6px 12px;
  text-align: left;
  width: 100%;
  white-space: nowrap;
}

.dropdown-item:hover {
  background: #27272a;
  color: #f4f4f5;
}

.dropdown-item.text-danger:hover {
  background: rgba(239, 68, 68, 0.1);
}
</style>
