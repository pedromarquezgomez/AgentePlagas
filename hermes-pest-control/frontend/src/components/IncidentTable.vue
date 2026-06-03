<script setup lang="ts">
import type { Incident } from '../services/api'
import {
  formatChannel,
  formatDispatchBucket,
  formatPestType,
  formatPriority,
  formatSeverity,
  formatStatus,
  formatTechnicianLevel,
  formatVisitType,
} from '../utils/labels'

defineProps<{
  incidents: Incident[]
}>()

const emit = defineEmits<{
  open: [incidentId: string]
  sort: [sortBy: string]
}>()

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

function formatDate(value: string | undefined): string {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

function operationalPriority(incident: Incident): string | null {
  return incident.operational_priority || incident.priority || null
}

function badgeClass(prefix: string, value: string | null | undefined): string {
  return value ? `${prefix}-${value.toLowerCase()}` : ''
}

function formatHours(value: number | null | undefined): string {
  return typeof value === 'number' ? `${value}h` : 'Sin dato'
}
</script>

<template>
  <div class="tableShell">
    <table class="incidentTable">
      <thead>
        <tr>
          <th>Acción</th>
          <th>Plaga</th>
          <th>Localidad</th>
          <th>Zona</th>
          <th>
            <button class="tableSortButton" type="button" @click="emit('sort', 'severity')">
              Severidad
            </button>
          </th>
          <th>
            <button class="tableSortButton" type="button" @click="emit('sort', 'priority')">
              Prioridad
            </button>
          </th>
          <th>Actuación</th>
          <th>Técnico</th>
          <th>
            <button class="tableSortButton" type="button" @click="emit('sort', 'sla_hours')">
              SLA
            </button>
          </th>
          <th>Cola</th>
          <th>Estado</th>
          <th>Canal</th>
          <th>
            <button class="tableSortButton" type="button" @click="emit('sort', 'created_at')">
              Fecha
            </button>
          </th>
          <th>Resumen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="incident in incidents" :key="incident.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', incident.id)">
              Abrir
            </button>
          </td>
          <td>{{ formatPestType(incident.pest_type) }}</td>
          <td>{{ formatValue(incident.location) }}</td>
          <td>{{ formatValue(incident.affected_area) }}</td>
          <td>
            <span class="badge" :class="badgeClass('severity', incident.severity)">
              {{ formatSeverity(incident.severity) }}
            </span>
          </td>
          <td>
            <span class="badge" :class="badgeClass('priority', operationalPriority(incident))">
              {{ formatPriority(operationalPriority(incident)) }}
            </span>
          </td>
          <td>{{ formatVisitType(incident.visit_type) }}</td>
          <td>{{ formatTechnicianLevel(incident.technician_level) }}</td>
          <td>{{ formatHours(incident.sla_hours) }}</td>
          <td>
            <span class="badge status">{{ formatDispatchBucket(incident.dispatch_bucket) }}</span>
          </td>
          <td>
            <span class="badge status">{{ formatStatus(incident.status) }}</span>
          </td>
          <td>{{ formatChannel(incident.channel) }}</td>
          <td>{{ formatDate(incident.created_at) }}</td>
          <td class="summaryCell">{{ formatValue(incident.summary) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
