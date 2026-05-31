<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createVisit,
  fetchDocuments,
  fetchTechnicians,
  fetchVisit,
  generateTechnicianBriefDocument,
  isUnauthorizedError,
  syncVisitCalendar,
  updateVisit,
  VISIT_STATUSES,
  type Technician,
  type OperationalDocument,
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
const documents = ref<OperationalDocument[]>([])
const technicians = ref<Technician[]>([])
const loading = ref(false)
const saving = ref(false)
const syncingCalendar = ref(false)
const documentGenerating = ref(false)
const error = ref<string | null>(null)
const documentsError = ref<string | null>(null)
const saveError = ref<string | null>(null)
const documentGenerateError = ref<string | null>(null)
const saveSuccess = ref(false)
const documentGenerateSuccess = ref(false)
const syncMessage = ref<string | null>(null)
const syncError = ref<string | null>(null)
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

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Sin dato'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
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
  syncMessage.value = null
  syncError.value = null

  try {
    technicians.value = await fetchTechnicians({ active: true, limit: 200 })
    if (isNew.value) {
      visit.value = null
      syncForm(null)
      return
    }

    const [loadedVisit, loadedDocuments] = await Promise.all([
      fetchVisit(props.visitId),
      fetchDocuments({ visit_id: props.visitId, limit: 100 }),
    ])
    visit.value = loadedVisit
    documents.value = loadedDocuments
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

async function loadDocuments(): Promise<void> {
  if (isNew.value) return

  try {
    documents.value = await fetchDocuments({ visit_id: props.visitId, limit: 100 })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    documentsError.value = err instanceof Error ? err.message : 'No se pudieron cargar los documentos'
    documents.value = []
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

async function generateTechnicianBrief(): Promise<void> {
  if (isNew.value) return

  documentGenerating.value = true
  documentGenerateError.value = null
  documentGenerateSuccess.value = false

  try {
    await generateTechnicianBriefDocument(props.visitId)
    documentGenerateSuccess.value = true
    await loadDocuments()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    documentGenerateError.value = err instanceof Error ? err.message : 'No se pudo generar el brief'
  } finally {
    documentGenerating.value = false
  }
}

async function synchronizeCalendar(): Promise<void> {
  if (isNew.value) return

  syncingCalendar.value = true
  syncMessage.value = null
  syncError.value = null

  try {
    const result = await syncVisitCalendar(props.visitId)
    visit.value = result.visit
    syncForm(result.visit)
    syncMessage.value = result.status === 'skipped'
      ? 'Sincronización omitida: Google Calendar está desactivado.'
      : 'Sincronizado correctamente.'
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    syncError.value = err instanceof Error ? err.message : 'No se pudo sincronizar el calendario'
  } finally {
    syncingCalendar.value = false
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

    <template v-else>
      <form class="editPanel widePanel" aria-label="Guardar visita" @submit.prevent="saveVisit">
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

      <section v-if="!isNew" class="editPanel widePanel calendarSyncPanel">
        <div class="sectionHeader">
          <div>
            <h3>Sincronización calendario</h3>
            <p class="sectionText">Google Calendar es opcional; Firestore sigue siendo la fuente de verdad.</p>
          </div>
          <button
            class="primaryButton"
            type="button"
            :disabled="syncingCalendar"
            @click="synchronizeCalendar"
          >
            {{ syncingCalendar ? 'Sincronizando...' : 'Sincronizar con calendario' }}
          </button>
        </div>

        <dl class="detailGrid">
          <div>
            <dt>Proveedor</dt>
            <dd>{{ formatValue(visit?.external_calendar_provider) }}</dd>
          </div>
          <div>
            <dt>Evento</dt>
            <dd>{{ formatValue(visit?.external_calendar_event_id) }}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>{{ formatValue(visit?.external_calendar_sync_status) }}</dd>
          </div>
          <div>
            <dt>Última sincronización</dt>
            <dd>{{ formatDate(visit?.external_calendar_last_synced_at) }}</dd>
          </div>
        </dl>

        <div v-if="visit?.external_calendar_error" class="stateMessage errorMessage">
          {{ visit.external_calendar_error }}
        </div>
        <p v-if="syncMessage" class="saveMessage">{{ syncMessage }}</p>
        <div v-if="syncError" class="stateMessage errorMessage">{{ syncError }}</div>
      </section>

      <section v-if="!isNew" class="editPanel widePanel">
        <div class="sectionHeader">
          <div>
            <h3>Documentos asociados</h3>
            <p class="sectionText">Documentos operativos internos vinculados a esta visita.</p>
          </div>
          <button
            class="primaryButton"
            type="button"
            :disabled="documentGenerating"
            @click="generateTechnicianBrief"
          >
            {{ documentGenerating ? 'Generando...' : 'Generar brief para técnico' }}
          </button>
        </div>

        <div v-if="documentsError" class="stateMessage errorMessage">{{ documentsError }}</div>
        <div v-else-if="documents.length === 0" class="stateMessage">
          No hay documentos asociados a esta visita.
        </div>
        <div v-else class="compactTableShell">
          <table class="incidentTable compactTable">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Título</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="document in documents" :key="document.id">
                <td>{{ document.document_type }}</td>
                <td>{{ document.title }}</td>
                <td><span class="badge status">{{ document.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="documentGenerateSuccess" class="saveMessage">Documento generado.</p>
        <div v-if="documentGenerateError" class="stateMessage errorMessage">{{ documentGenerateError }}</div>
      </section>
    </template>
  </section>
</template>
