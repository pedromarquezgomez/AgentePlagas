<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listIncidents, updateIncident } from '../api/incidents'
import type { Incident } from '../api/types'
import { ApiError } from '../api/types'

const incidents = ref<Incident[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

async function fetchIncidents() {
  loading.value = true
  errorMsg.value = null
  try {
    incidents.value = await listIncidents()
  } catch (err) {
    if (err instanceof ApiError) {
      errorMsg.value = `${err.message} (Código: ${err.code || 'N/A'}, Status: ${err.status})`
    } else {
      errorMsg.value = err instanceof Error ? err.message : 'Error inesperado al cargar incidentes'
    }
  } finally {
    loading.value = false
  }
}

async function handleMarkAsScheduled(incidentId: string) {
  try {
    await updateIncident(incidentId, { status: 'scheduled' })
    await fetchIncidents()
  } catch (err) {
    if (err instanceof ApiError) {
      alert(`Error al actualizar: ${err.message}`)
    } else {
      alert(err instanceof Error ? err.message : 'No se pudo actualizar el incidente')
    }
  }
}

onMounted(() => {
  fetchIncidents()
})
</script>

<template>
  <div class="operations-center-example" style="padding: 20px; font-family: sans-serif;">
    <h2>Centro de Operaciones (Ejemplo Capa API)</h2>

    <div v-if="loading" class="loading-state">
      Cargando incidencias desde el backend...
    </div>

    <div v-else-if="errorMsg" class="error-state" style="color: #9a3412; font-weight: bold; background: #fff7ed; padding: 12px; border: 1px solid #fed7aa; border-radius: 6px;">
      ⚠️ Error: {{ errorMsg }}
    </div>

    <div v-else-if="incidents.length === 0" class="empty-state">
      No se encontraron incidencias en el sistema.
    </div>

    <div v-else class="incidents-list">
      <ul style="padding: 0;">
        <li 
          v-for="incident in incidents" 
          :key="incident.id" 
          style="margin-bottom: 16px; list-style: none; border: 1px solid #d8dee5; border-radius: 8px; padding: 16px; background: #ffffff;"
        >
          <div style="margin-bottom: 6px;">
            <strong>ID:</strong> {{ incident.id }} | 
            <strong>Canal:</strong> {{ incident.channel }}
          </div>
          <div style="margin-bottom: 6px;">
            <strong>Plaga:</strong> {{ incident.pest_type || 'No identificada' }} | 
            <strong>Ubicación:</strong> {{ incident.location || 'N/A' }} | 
            <strong>Zona:</strong> {{ incident.affected_area || 'N/A' }}
          </div>
          <div style="margin-bottom: 8px;">
            <strong>Estado:</strong> {{ incident.status }} | 
            <strong>Prioridad:</strong> {{ incident.priority }}
          </div>
          <div v-if="incident.summary" style="font-style: italic; color: #5c6773; background: #f8fafc; padding: 8px; border-radius: 4px; margin-bottom: 10px;">
            "{{ incident.summary }}"
          </div>
          <button 
            v-if="incident.status === 'ready_for_scheduling'"
            @click="handleMarkAsScheduled(incident.id)"
            style="cursor: pointer; padding: 6px 12px; font-weight: bold; background: #235b8c; color: white; border: none; border-radius: 4px;"
          >
            Marcar como Agendada (scheduled)
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
