<script setup lang="ts">
import type { Visit } from '../services/api'
import { formatStatus } from '../utils/labels'

defineProps<{
  visits: Visit[]
}>()

const emit = defineEmits<{
  open: [visitId: string]
}>()

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}
</script>

<template>
  <div class="tableShell">
    <table class="incidentTable">
      <thead>
        <tr>
          <th>Acción</th>
          <th>Incidencia</th>
          <th>Técnico</th>
          <th>Inicio</th>
          <th>Fin</th>
          <th>Estado</th>
          <th>Dirección</th>
          <th>Notas</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="visit in visits" :key="visit.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', visit.id)">
              Abrir
            </button>
          </td>
          <td>{{ visit.incident_id }}</td>
          <td>{{ formatValue(visit.technician_id) }}</td>
          <td>{{ formatDate(visit.scheduled_start) }}</td>
          <td>{{ formatDate(visit.scheduled_end) }}</td>
          <td><span class="badge status">{{ formatStatus(visit.status) }}</span></td>
          <td>{{ formatValue(visit.address) }}</td>
          <td class="summaryCell">{{ formatValue(visit.notes) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
