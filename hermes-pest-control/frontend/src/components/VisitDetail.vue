<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createVisit,
  fetchTechnicians,
  fetchVisit,
  isUnauthorizedError,
  updateVisit,
  VISIT_STATUSES,
  type Technician,
  type Visit,
  type VisitStatus,
} from '../services/api'

const props = defineProps<{
  visitId: string
}>()

const emit = defineEmits<{
  back: []
  created: [visitId: string]
  unauthorized: []
}>()

const isNew = computed(() => props.visitId === 'new')
const visit = ref<Visit | null>(null)
const technicians = ref<Technician[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const formIncidentId = ref('')
const formTechnicianId = ref('')
const formScheduledStart = ref('')
const formScheduledEnd = ref('')
const formStatus = ref<VisitStatus>('draft')
const formAddress = ref('')
const formNotes = ref('')

function toInputDate(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value.slice(0, 16)
  const offset = date.getTimezoneOffset()
  const localDate = new Date(date.getTime() - offset * 60000)
  return localDate.toISOString().slice(0, 16)
}

function isVisitStatus(value: string): value is VisitStatus {
  return VISIT_STATUSES.includes(value as VisitStatus)
}

function syncForm(nextVisit: Visit | null): void {
  formIncidentId.value = nextVisit?.incident_id ?? ''
  formTechnicianId.value = nextVisit?.technician_id ?? ''
  formScheduledStart.value = toInputDate(nextVisit?.scheduled_start)
  formScheduledEnd.value = toInputDate(nextVisit?.scheduled_end)
  if (nextVisit?.status && isVisitStatus(nextVisit.status)) {
    formStatus.value = nextVisit.status
  } else {
    formStatus.value = 'draft'
  }
  formAddress.value = nextVisit?.address ?? ''
  formNotes.value = nextVisit?.notes ?? ''
}

async function loadVisit(): Promise<void> {
  loading.value = true
  error.value = null
  saveError.value = null
  saveSuccess.value = false

  try {
    technicians.value = await fetchTechnicians({ active: true, limit: 200 })
    if (isNew.value) {
      visit.value = null
      syncForm(null)
      return
    }

    const loadedVisit = await fetchVisit(props.visitId)
    visit.value = loadedVisit
    syncForm(loadedVisit)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la visita'
    visit.value = null
  } finally {
    loading.value = false
  }
}

async function saveVisit(): Promise<void> {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  const payload = {
    incident_id: formIncidentId.value.trim(),
    technician_id: formTechnicianId.value || null,
    scheduled_start: formScheduledStart.value || null,
    scheduled_end: formScheduledEnd.value || null,
    status: formStatus.value,
    address: formAddress.value.trim() || null,
    notes: formNotes.value.trim() || null,
  }

  try {
    if (isNew.value) {
      const createdVisit = await createVisit(payload)
      visit.value = createdVisit
      syncForm(createdVisit)
      saveSuccess.value = true
      emit('created', createdVisit.id)
      return
    }

    await updateVisit(props.visitId, {
      technician_id: payload.technician_id,
      scheduled_start: payload.scheduled_start,
      scheduled_end: payload.scheduled_end,
      status: payload.status,
      address: payload.address,
      notes: payload.notes,
    })
    const refreshedVisit = await fetchVisit(props.visitId)
    visit.value = refreshedVisit
    syncForm(refreshedVisit)
    saveSuccess.value = true
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar la visita'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.visitId,
  () => {
    void loadVisit()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">{{ isNew ? 'Nueva visita' : 'Detalle de visita' }}</p>
        <h2>{{ formIncidentId || 'Visita' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando visita...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <form v-else class="editPanel widePanel" aria-label="Guardar visita" @submit.prevent="saveVisit">
      <label>
        Incidencia
        <input v-model="formIncidentId" :disabled="saving || !isNew" required type="text" />
      </label>

      <label>
        Técnico
        <select v-model="formTechnicianId" :disabled="saving">
          <option value="">Sin asignar</option>
          <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
            {{ technician.name }}
          </option>
        </select>
      </label>

      <label>
        Inicio
        <input v-model="formScheduledStart" :disabled="saving" type="datetime-local" />
      </label>

      <label>
        Fin
        <input v-model="formScheduledEnd" :disabled="saving" type="datetime-local" />
      </label>

      <label>
        Estado
        <select v-model="formStatus" :disabled="saving">
          <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
            {{ status }}
          </option>
        </select>
      </label>

      <label>
        Dirección
        <input v-model="formAddress" :disabled="saving" type="text" />
      </label>

      <label>
        Notas
        <textarea v-model="formNotes" :disabled="saving" rows="8" />
      </label>

      <div class="formActions">
        <button class="primaryButton" type="submit" :disabled="saving || !formIncidentId.trim()">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
        <span v-if="saveSuccess" class="saveMessage">Guardado correctamente.</span>
      </div>

      <div v-if="saveError" class="stateMessage errorMessage">{{ saveError }}</div>
    </form>
  </section>
</template>
