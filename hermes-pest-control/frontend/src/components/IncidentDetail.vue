<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  fetchIncident,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  isUnauthorizedError,
  updateIncident,
  type Incident,
  type IncidentPriority,
  type IncidentStatus,
} from '../services/api'

const props = defineProps<{
  incidentId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const incident = ref<Incident | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const formStatus = ref<IncidentStatus>('pending_review')
const formPriority = ref<IncidentPriority>('medium')
const formInternalNotes = ref('')

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

function formatDate(value: string | undefined): string {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function isIncidentStatus(value: string): value is IncidentStatus {
  return INCIDENT_STATUSES.includes(value as IncidentStatus)
}

function isIncidentPriority(value: string): value is IncidentPriority {
  return INCIDENT_PRIORITIES.includes(value as IncidentPriority)
}

function syncForm(nextIncident: Incident): void {
  if (isIncidentStatus(nextIncident.status)) {
    formStatus.value = nextIncident.status
  }
  if (isIncidentPriority(nextIncident.priority)) {
    formPriority.value = nextIncident.priority
  }
  formInternalNotes.value = nextIncident.internal_notes ?? ''
}

async function loadIncident(): Promise<void> {
  loading.value = true
  error.value = null
  saveError.value = null
  saveSuccess.value = false

  try {
    const loadedIncident = await fetchIncident(props.incidentId)
    incident.value = loadedIncident
    syncForm(loadedIncident)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la incidencia'
    incident.value = null
  } finally {
    loading.value = false
  }
}

async function saveIncident(): Promise<void> {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  try {
    await updateIncident(props.incidentId, {
      status: formStatus.value,
      priority: formPriority.value,
      internal_notes: formInternalNotes.value,
    })
    const refreshedIncident = await fetchIncident(props.incidentId)
    incident.value = refreshedIncident
    syncForm(refreshedIncident)
    saveSuccess.value = true
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar la incidencia'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.incidentId,
  () => {
    void loadIncident()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">Detalle de incidencia</p>
        <h2>{{ incident ? formatValue(incident.pest_type) : 'Incidencia' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando incidencia...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <div v-else-if="incident" class="detailLayout">
      <section class="detailPanel" aria-label="Datos de la incidencia">
        <dl class="detailGrid">
          <div>
            <dt>Tipo de plaga</dt>
            <dd>{{ formatValue(incident.pest_type) }}</dd>
          </div>
          <div>
            <dt>Localidad</dt>
            <dd>{{ formatValue(incident.location) }}</dd>
          </div>
          <div>
            <dt>Zona afectada</dt>
            <dd>{{ formatValue(incident.affected_area) }}</dd>
          </div>
          <div>
            <dt>Prioridad</dt>
            <dd>
              <span class="badge" :class="`priority-${incident.priority}`">
                {{ incident.priority }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd><span class="badge status">{{ incident.status }}</span></dd>
          </div>
          <div>
            <dt>Canal</dt>
            <dd>{{ incident.channel }}</dd>
          </div>
          <div>
            <dt>Fecha creación</dt>
            <dd>{{ formatDate(incident.created_at) }}</dd>
          </div>
          <div>
            <dt>Fecha actualización</dt>
            <dd>{{ formatDate(incident.updated_at) }}</dd>
          </div>
        </dl>

        <div class="summaryBlock">
          <h3>Resumen</h3>
          <p>{{ formatValue(incident.summary) }}</p>
        </div>
      </section>

      <form class="editPanel" aria-label="Actualizar incidencia" @submit.prevent="saveIncident">
        <label>
          Estado
          <select v-model="formStatus" :disabled="saving">
            <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
              {{ status }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="formPriority" :disabled="saving">
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ priority }}
            </option>
          </select>
        </label>

        <label>
          Notas internas
          <textarea
            v-model="formInternalNotes"
            :disabled="saving"
            placeholder="Notas visibles solo para el equipo"
            rows="8"
          />
        </label>

        <div class="formActions">
          <button class="primaryButton" type="submit" :disabled="saving">
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </button>
          <span v-if="saveSuccess" class="saveMessage">Guardado correctamente.</span>
        </div>

        <div v-if="saveError" class="stateMessage errorMessage">{{ saveError }}</div>
      </form>
    </div>
  </section>
</template>
