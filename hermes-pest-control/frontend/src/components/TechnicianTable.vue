<script setup lang="ts">
import type { Technician } from '../services/api'

defineProps<{
  technicians: Technician[]
}>()

const emit = defineEmits<{
  open: [technicianId: string]
}>()

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}
</script>

<template>
  <div class="tableShell">
    <table class="incidentTable">
      <thead>
        <tr>
          <th>Acción</th>
          <th>Nombre</th>
          <th>Teléfono</th>
          <th>Email</th>
          <th>Activo</th>
          <th>Zona</th>
          <th>Skills</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="technician in technicians" :key="technician.id">
          <td>
            <button class="linkButton" type="button" @click="emit('open', technician.id)">
              Abrir
            </button>
          </td>
          <td>{{ technician.name }}</td>
          <td>{{ formatValue(technician.phone) }}</td>
          <td>{{ formatValue(technician.email) }}</td>
          <td>
            <span class="badge status">{{ technician.active ? 'activo' : 'inactivo' }}</span>
          </td>
          <td>{{ formatValue(technician.service_area) }}</td>
          <td class="summaryCell">{{ technician.skills.join(', ') || 'Sin dato' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
