<script setup lang="ts">
import type { Incident } from '../services/api'

defineProps<{
  incidents: Incident[]
}>()

const emit = defineEmits<{
  open: [incidentId: string]
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
          <th>Prioridad</th>
          <th>Estado</th>
          <th>Canal</th>
          <th>Fecha</th>
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
          <td>{{ formatValue(incident.pest_type) }}</td>
          <td>{{ formatValue(incident.location) }}</td>
          <td>{{ formatValue(incident.affected_area) }}</td>
          <td>
            <span class="badge" :class="`priority-${incident.priority}`">
              {{ incident.priority }}
            </span>
          </td>
          <td>
            <span class="badge status">{{ incident.status }}</span>
          </td>
          <td>{{ incident.channel }}</td>
          <td>{{ formatDate(incident.created_at) }}</td>
          <td class="summaryCell">{{ formatValue(incident.summary) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
