<script setup lang="ts">
import type { ShadowDecisionRecord } from '../services/api'
import {
  agreementClass,
  formatAction,
  formatAgreement,
  formatChannel,
  formatFallback,
  formatPlainValue,
  formatPriority,
} from '../utils/labels'

defineProps<{
  records: ShadowDecisionRecord[]
}>()

const emit = defineEmits<{
  open: [recordId: string]
}>()

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
          <th>Fecha</th>
          <th>Canal</th>
          <th>Conversación</th>
          <th>Decisión del sistema actual</th>
          <th>Decisión de la IA</th>
          <th>Prioridad actual</th>
          <th>Prioridad IA</th>
          <th>Resultado</th>
          <th>Error IA</th>
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
          <td>{{ formatChannel(record.channel) }}</td>
          <td>{{ record.conversation_id }}</td>
          <td><span class="badge status">{{ formatAction(record.primary_action_type) }}</span></td>
          <td><span class="badge status">{{ formatAction(record.shadow_action_type) }}</span></td>
          <td>{{ formatPriority(record.primary_priority) }}</td>
          <td>{{ formatPriority(record.shadow_priority) }}</td>
          <td>
            <span class="badge" :class="agreementClass(record.agreement_summary)">
              {{ formatAgreement(record.agreement_summary) }}
            </span>
          </td>
          <td>
            {{ record.shadow_error ? formatPlainValue(record.shadow_error) : formatFallback(record.shadow_fallback_used) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
