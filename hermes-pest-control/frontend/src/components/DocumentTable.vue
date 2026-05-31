<script setup lang="ts">
import type { OperationalDocument } from '../services/api'

defineProps<{
  documents: OperationalDocument[]
}>()

const emit = defineEmits<{
  open: [documentId: string]
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
          <th>Tipo</th>
          <th>Título</th>
          <th>Estado</th>
          <th>Incidencia</th>
          <th>Visita</th>
          <th>Generado por</th>
          <th>Fecha</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="document in documents" :key="document.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', document.id)">
              Abrir
            </button>
          </td>
          <td>{{ document.document_type }}</td>
          <td class="summaryCell">{{ document.title }}</td>
          <td><span class="badge status">{{ document.status }}</span></td>
          <td>{{ formatValue(document.incident_id) }}</td>
          <td>{{ formatValue(document.visit_id) }}</td>
          <td>{{ document.generated_by }}</td>
          <td>{{ formatDate(document.created_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
