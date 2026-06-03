<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  createVisit,
  fetchDocuments,
  fetchIncident,
  fetchTechnicians,
  fetchVisits,
  generateIncidentSummaryDocument,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  isUnauthorizedError,
  updateIncident,
  VISIT_STATUSES,
  type Incident,
  type IncidentPriority,
  type IncidentStatus,
  type OperationalDocument,
  type Technician,
  type Visit,
  type VisitStatus,
} from '../services/api'
import {
  formatDispatchBucket,
  formatDocumentType,
  formatGeneratedBy,
  formatPestType,
  formatPriority,
  formatSeverity,
  formatStatus,
  formatTechnicianLevel,
  formatVisitType,
} from '../utils/labels'

const props = defineProps<{
  incidentId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const incident = ref<Incident | null>(null)
const visits = ref<Visit[]>([])
const documents = ref<OperationalDocument[]>([])
const technicians = ref<Technician[]>([])
const loading = ref(false)
const visitsLoading = ref(false)
const documentsLoading = ref(false)
const saving = ref(false)
const visitSaving = ref(false)
const documentGenerating = ref(false)
const error = ref<string | null>(null)
const visitsError = ref<string | null>(null)
const documentsError = ref<string | null>(null)
const saveError = ref<string | null>(null)
const visitSaveError = ref<string | null>(null)
const documentGenerateError = ref<string | null>(null)
const saveSuccess = ref(false)
const visitSaveSuccess = ref(false)
const documentGenerateSuccess = ref(false)
const formStatus = ref<IncidentStatus>('pending_review')
const formPriority = ref<IncidentPriority>('medium')
const formInternalNotes = ref('')
const visitTechnicianId = ref('')
const visitScheduledStart = ref('')
const visitScheduledEnd = ref('')
const visitStatus = ref<VisitStatus>('draft')
const visitAddress = ref('')
const visitNotes = ref('')

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

function formatVisitDate(value: string | null | undefined): string {
  return formatDate(value ?? undefined)
}

function formatHours(value: number | null | undefined): string {
  return typeof value === 'number' ? `${value}h` : 'Sin dato'
}

function operationalPriority(nextIncident: Incident): string | null {
  return nextIncident.operational_priority || nextIncident.priority || null
}

function syncForm(nextIncident: Incident): void {
  if (isIncidentStatus(nextIncident.status)) {
    formStatus.value = nextIncident.status
  }
  if (isIncidentPriority(nextIncident.priority)) {
    formPriority.value = nextIncident.priority
  }
  formInternalNotes.value = nextIncident.internal_notes ?? ''
  visitAddress.value = nextIncident.location ?? ''
}

async function loadVisits(): Promise<void> {
  visitsLoading.value = true
  visitsError.value = null

  try {
    const [loadedVisits, loadedTechnicians] = await Promise.all([
      fetchVisits({ incident_id: props.incidentId, limit: 100 }),
      fetchTechnicians({ active: true, limit: 200 }),
    ])
    visits.value = loadedVisits
    technicians.value = loadedTechnicians
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    visitsError.value = err instanceof Error ? err.message : 'No se pudieron cargar las visitas'
    visits.value = []
  } finally {
    visitsLoading.value = false
  }
}

async function loadDocuments(): Promise<void> {
  documentsLoading.value = true
  documentsError.value = null

  try {
    documents.value = await fetchDocuments({ incident_id: props.incidentId, limit: 100 })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    documentsError.value = err instanceof Error ? err.message : 'No se pudieron cargar los documentos'
    documents.value = []
  } finally {
    documentsLoading.value = false
  }
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
    await Promise.all([loadVisits(), loadDocuments()])
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

async function generateSummaryDocument(): Promise<void> {
  documentGenerating.value = true
  documentGenerateError.value = null
  documentGenerateSuccess.value = false

  try {
    await generateIncidentSummaryDocument(props.incidentId)
    documentGenerateSuccess.value = true
    await loadDocuments()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    documentGenerateError.value = err instanceof Error ? err.message : 'No se pudo generar el resumen'
  } finally {
    documentGenerating.value = false
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

async function createIncidentVisit(): Promise<void> {
  visitSaving.value = true
  visitSaveError.value = null
  visitSaveSuccess.value = false

  try {
    await createVisit({
      incident_id: props.incidentId,
      technician_id: visitTechnicianId.value || null,
      scheduled_start: visitScheduledStart.value || null,
      scheduled_end: visitScheduledEnd.value || null,
      status: visitStatus.value,
      address: visitAddress.value.trim() || null,
      notes: visitNotes.value.trim() || null,
    })
    visitTechnicianId.value = ''
    visitScheduledStart.value = ''
    visitScheduledEnd.value = ''
    visitStatus.value = 'draft'
    visitNotes.value = ''
    visitSaveSuccess.value = true
    await loadVisits()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    visitSaveError.value = err instanceof Error ? err.message : 'No se pudo crear la visita'
  } finally {
    visitSaving.value = false
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

      <section class="detailPanel" aria-label="Evaluación operativa">
        <h3>Evaluación Operativa</h3>
        <dl class="detailGrid">
          <div>
            <dt>Plaga detectada</dt>
            <dd>{{ formatPestType(incident.pest_type) }}</dd>
          </div>
          <div>
            <dt>Confianza</dt>
            <dd>{{ formatValue(incident.confidence) }}</dd>
          </div>
          <div>
            <dt>Severidad</dt>
            <dd>
              <span class="badge" :class="`severity-${(incident.severity || '').toLowerCase()}`">
                {{ formatSeverity(incident.severity) }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Prioridad operativa</dt>
            <dd>
              <span class="badge" :class="`priority-${(operationalPriority(incident) || '').toLowerCase()}`">
                {{ formatPriority(operationalPriority(incident)) }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Tiempo recomendado</dt>
            <dd>{{ formatHours(incident.response_hours) }}</dd>
          </div>
        </dl>
        <div class="summaryBlock">
          <h4>Motivo de evaluación</h4>
          <p>{{ formatValue(incident.assessment_reason) }}</p>
        </div>
      </section>

      <section class="detailPanel" aria-label="Dispatch Assessment">
        <h3>Dispatch Assessment</h3>
        <dl class="detailGrid">
          <div>
            <dt>Tipo de actuación</dt>
            <dd>{{ formatVisitType(incident.visit_type) }}</dd>
          </div>
          <div>
            <dt>Nivel técnico requerido</dt>
            <dd>{{ formatTechnicianLevel(incident.technician_level) }}</dd>
          </div>
          <div>
            <dt>SLA</dt>
            <dd>{{ formatHours(incident.sla_hours) }}</dd>
          </div>
          <div>
            <dt>Cola operativa</dt>
            <dd><span class="badge status">{{ formatDispatchBucket(incident.dispatch_bucket) }}</span></dd>
          </div>
        </dl>
      </section>

      <form class="editPanel" aria-label="Actualizar incidencia" @submit.prevent="saveIncident">
        <label>
          Estado
          <select v-model="formStatus" :disabled="saving">
            <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="formPriority" :disabled="saving">
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ formatPriority(priority) }}
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

      <section class="detailPanel fullWidthPanel" aria-label="Documentos asociados">
        <div class="sectionHeader">
          <div>
            <h3>Documentos asociados</h3>
            <p class="sectionText">Documentos operativos internos vinculados a esta incidencia.</p>
          </div>
          <div class="formActions">
            <button class="secondaryButton" type="button" :disabled="documentsLoading" @click="loadDocuments">
              Actualizar
            </button>
            <button class="primaryButton" type="button" :disabled="documentGenerating" @click="generateSummaryDocument">
              {{ documentGenerating ? 'Generando...' : 'Generar resumen de incidencia' }}
            </button>
          </div>
        </div>

        <div v-if="documentsLoading" class="stateMessage">Cargando documentos...</div>
        <div v-else-if="documentsError" class="stateMessage errorMessage">{{ documentsError }}</div>
        <div v-else-if="documents.length === 0" class="stateMessage">
          No hay documentos asociados a esta incidencia.
        </div>
        <div v-else class="compactTableShell">
          <table class="incidentTable compactTable">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Título</th>
                <th>Estado</th>
                <th>Generado por</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="document in documents" :key="document.id">
                <td>{{ formatDocumentType(document.document_type) }}</td>
                <td>{{ document.title }}</td>
                <td><span class="badge status">{{ formatStatus(document.status) }}</span></td>
                <td>{{ formatGeneratedBy(document.generated_by) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="documentGenerateSuccess" class="saveMessage">Documento generado.</p>
        <div v-if="documentGenerateError" class="stateMessage errorMessage">{{ documentGenerateError }}</div>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Visitas asociadas">
        <div class="sectionHeader">
          <div>
            <h3>Visitas asociadas</h3>
            <p class="sectionText">Agenda manual vinculada a esta incidencia.</p>
          </div>
          <button class="secondaryButton" type="button" :disabled="visitsLoading" @click="loadVisits">
            Actualizar
          </button>
        </div>

        <div v-if="visitsLoading" class="stateMessage">Cargando visitas...</div>
        <div v-else-if="visitsError" class="stateMessage errorMessage">{{ visitsError }}</div>
        <div v-else-if="visits.length === 0" class="stateMessage">
          No hay visitas asociadas a esta incidencia.
        </div>
        <div v-else class="compactTableShell">
          <table class="incidentTable compactTable">
            <thead>
              <tr>
                <th>Estado</th>
                <th>Técnico</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Dirección</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="visit in visits" :key="visit.id">
                <td><span class="badge status">{{ formatStatus(visit.status) }}</span></td>
                <td>{{ formatValue(visit.technician_id) }}</td>
                <td>{{ formatVisitDate(visit.scheduled_start) }}</td>
                <td>{{ formatVisitDate(visit.scheduled_end) }}</td>
                <td>{{ formatValue(visit.address) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <form class="inlineForm" aria-label="Crear visita asociada" @submit.prevent="createIncidentVisit">
          <label>
            Técnico
            <select v-model="visitTechnicianId" :disabled="visitSaving">
              <option value="">Sin asignar</option>
              <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
                {{ technician.name }}
              </option>
            </select>
          </label>

          <label>
            Inicio
            <input v-model="visitScheduledStart" :disabled="visitSaving" type="datetime-local" />
          </label>

          <label>
            Fin
            <input v-model="visitScheduledEnd" :disabled="visitSaving" type="datetime-local" />
          </label>

          <label>
            Estado
            <select v-model="visitStatus" :disabled="visitSaving">
              <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
                {{ formatStatus(status) }}
              </option>
            </select>
          </label>

          <label>
            Dirección
            <input v-model="visitAddress" :disabled="visitSaving" type="text" />
          </label>

          <label class="inlineFormWide">
            Notas
            <textarea v-model="visitNotes" :disabled="visitSaving" rows="4" />
          </label>

          <div class="formActions inlineFormWide">
            <button class="primaryButton" type="submit" :disabled="visitSaving">
              {{ visitSaving ? 'Creando...' : 'Crear visita' }}
            </button>
            <span v-if="visitSaveSuccess" class="saveMessage">Visita creada.</span>
          </div>

          <div v-if="visitSaveError" class="stateMessage errorMessage inlineFormWide">
            {{ visitSaveError }}
          </div>
        </form>
      </section>
    </div>
  </section>
</template>
