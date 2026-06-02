<script setup lang="ts">
import type { HumanReviewItem } from '../services/api'
import { formatChannel, formatPriority, formatReason, formatStatus } from '../utils/labels'

defineProps<{
  items: HumanReviewItem[]
}>()

const emit = defineEmits<{
  open: [itemId: string]
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
          <th>Prioridad</th>
          <th>Razón</th>
          <th>Estado</th>
          <th>Canal</th>
          <th>Fecha</th>
          <th>Incidencia</th>
          <th>Resumen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', item.id)">
              Abrir
            </button>
          </td>
          <td>
            <span class="badge" :class="`priority-${item.priority}`">
              {{ formatPriority(item.priority) }}
            </span>
          </td>
          <td>{{ formatReason(item.reason) }}</td>
          <td><span class="badge status">{{ formatStatus(item.status) }}</span></td>
          <td>{{ formatChannel(item.channel) }}</td>
          <td>{{ formatDate(item.created_at) }}</td>
          <td>{{ formatValue(item.incident_id) }}</td>
          <td class="summaryCell">{{ formatValue(item.summary) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
