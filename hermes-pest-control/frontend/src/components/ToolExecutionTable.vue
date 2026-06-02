<script setup lang="ts">
import type { ToolExecutionRecord } from '../services/api'
import {
  formatBooleanYesNo,
  formatExecutionStatus,
  formatReviewStatus,
  formatRiskLevel,
  formatToolDecision,
  formatToolName,
  formatToolProvider,
} from '../utils/labels'

defineProps<{
  records: ToolExecutionRecord[]
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
          <th>Herramienta</th>
          <th>Proveedor</th>
          <th>Operación</th>
          <th>Riesgo</th>
          <th>Decisión</th>
          <th>Estado revisión</th>
          <th>Requiere aprobación</th>
          <th>Resultado ejecución</th>
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
          <td>{{ formatToolName(record.tool_name) }}</td>
          <td>{{ formatToolProvider(record.provider) }}</td>
          <td>{{ record.action }}</td>
          <td>{{ formatRiskLevel(record.risk_level) }}</td>
          <td><span class="badge status">{{ formatToolDecision(record.decision) }}</span></td>
          <td><span class="badge status">{{ formatReviewStatus(record.review_status) }}</span></td>
          <td>{{ formatBooleanYesNo(record.requires_approval) }}</td>
          <td>{{ formatExecutionStatus(record.execution_status) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
