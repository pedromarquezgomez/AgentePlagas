<script setup lang="ts">
import type { ShadowDecisionRecord } from '../services/api'

defineProps<{
  records: ShadowDecisionRecord[]
}>()

const emit = defineEmits<{
  open: [recordId: string]
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

function formatBoolean(value: boolean | null | undefined): string {
  if (value === true) return 'sí'
  if (value === false) return 'no'
  return 'Sin dato'
}
</script>

<template>
  <div class="tableShell">
    <table class="incidentTable">
      <thead>
        <tr>
          <th>Acción</th>
          <th>Fecha</th>
          <th>Canal</th>
          <th>Conversación</th>
          <th>Primary action</th>
          <th>Shadow action</th>
          <th>Primary priority</th>
          <th>Shadow priority</th>
          <th>Agreement</th>
          <th>Fallback</th>
          <th>Error</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="record in records" :key="record.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', record.id)">
              Abrir
            </button>
          </td>
          <td>{{ formatDate(record.created_at) }}</td>
          <td>{{ record.channel }}</td>
          <td>{{ record.conversation_id }}</td>
          <td><span class="badge status">{{ record.primary_action_type }}</span></td>
          <td><span class="badge status">{{ formatValue(record.shadow_action_type) }}</span></td>
          <td>{{ formatValue(record.primary_priority) }}</td>
          <td>{{ formatValue(record.shadow_priority) }}</td>
          <td><span class="badge">{{ record.agreement_summary }}</span></td>
          <td>{{ formatBoolean(record.shadow_fallback_used) }}</td>
          <td>{{ formatValue(record.shadow_error) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
