<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  executeToolExecutionRecord,
  fetchToolExecutionRecord,
  isUnauthorizedError,
  TOOL_REVIEW_STATUSES,
  updateToolExecutionRecord,
  type ToolExecutionRecord,
  type ToolReviewStatus,
} from '../services/api'
import {
  formatBooleanYesNo,
  formatExecutionStatus,
  formatReviewStatus,
  formatRiskLevel,
  formatToolDecision,
  formatToolName,
  formatToolProvider,
} from '../utils/labels'

const props = defineProps<{
  executionId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const record = ref<ToolExecutionRecord | null>(null)
const loading = ref(false)
const saving = ref(false)
const executing = ref(false)
const error = ref<string | null>(null)
const savedMessage = ref<string | null>(null)
const reviewStatus = ref<ToolReviewStatus>('proposed')
const reviewerNotes = ref('')
const reviewedBy = ref('')
const approvedPayloadText = ref('{}')

const formattedTarget = computed(() => formatJson(record.value?.metadata?.target))
const formattedPayload = computed(() => formatJson(record.value?.metadata?.payload ?? record.value?.approved_payload))
const formattedApprovedPayload = computed(() => formatJson(record.value?.approved_payload))
const formattedExecutionResult = computed(() => formatJson(record.value?.execution_result))
const formattedMetadata = computed(() => formatJson(record.value?.metadata))
const canExecute = computed(() => {
  if (!record.value || record.value.executed) return false
  if (record.value.review_status !== 'approved') return false
  return (
    (record.value.tool_name === 'gmail.create_draft' && record.value.action === 'create_draft') ||
    (record.value.tool_name === 'schedule_visit_tool' && record.value.action === 'schedule_visit')
  )
})

const executeButtonLabel = computed(() => {
  if (record.value?.tool_name === 'schedule_visit_tool') {
    return 'Agendar visita en Google Calendar'
  }
  return 'Crear borrador en Gmail'
})

function formatDate(value: string | undefined | null): string {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatJson(value: unknown): string {
  if (!value || (typeof value === 'object' && Object.keys(value).length === 0)) {
    return '{}'
  }
  return JSON.stringify(value, null, 2)
}

function hydrateForm(nextRecord: ToolExecutionRecord): void {
  reviewStatus.value = (nextRecord.review_status as ToolReviewStatus) || 'proposed'
  reviewerNotes.value = nextRecord.reviewer_notes ?? ''
  reviewedBy.value = nextRecord.reviewed_by ?? ''
  approvedPayloadText.value = formatJson(nextRecord.approved_payload)
}

async function loadRecord(): Promise<void> {
  loading.value = true
  error.value = null
  savedMessage.value = null

  try {
    const loadedRecord = await fetchToolExecutionRecord(props.executionId)
    record.value = loadedRecord
    hydrateForm(loadedRecord)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la acción IA'
    record.value = null
  } finally {
    loading.value = false
  }
}

function parseApprovedPayload(): Record<string, unknown> | null {
  const trimmed = approvedPayloadText.value.trim()
  if (!trimmed || trimmed === '{}') return null
  const parsed = JSON.parse(trimmed)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('El payload aprobado debe ser un objeto JSON.')
  }
  return parsed as Record<string, unknown>
}

async function saveReview(nextStatus?: ToolReviewStatus): Promise<void> {
  if (!record.value) return
  saving.value = true
  error.value = null
  savedMessage.value = null

  try {
    const status = nextStatus ?? reviewStatus.value
    const updatedRecord = await updateToolExecutionRecord(record.value.id, {
      review_status: status,
      reviewer_notes: reviewerNotes.value.trim() || null,
      reviewed_by: reviewedBy.value.trim() || null,
      approved_payload: parseApprovedPayload(),
    })
    record.value = updatedRecord
    hydrateForm(updatedRecord)
    savedMessage.value = 'Revisión guardada. La herramienta no se ha ejecutado.'
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo guardar la revisión'
  } finally {
    saving.value = false
  }
}

async function executeAction(): Promise<void> {
  if (!record.value || !canExecute.value) return
  executing.value = true
  error.value = null
  savedMessage.value = null

  try {
    const updatedRecord = await executeToolExecutionRecord(record.value.id)
    record.value = updatedRecord
    hydrateForm(updatedRecord)
    if (record.value.tool_name === 'schedule_visit_tool') {
      savedMessage.value = 'Visita agendada con éxito en Google Calendar.'
    } else {
      savedMessage.value = 'Borrador creado en Gmail. No se ha enviado ningún correo.'
    }
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo ejecutar la acción'
  } finally {
    executing.value = false
  }
}

watch(
  () => props.executionId,
  () => {
    void loadRecord()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">Detalle de acción IA</p>
        <h2>{{ record ? formatToolName(record.tool_name) : 'Acción IA' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando acción IA...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <div v-else-if="record" class="detailLayout">
      <section class="detailPanel fullWidthPanel" aria-label="Aviso de seguridad de acciones IA">
        <div class="infoPanel">
          Aprobar una acción no ejecuta la herramienta externa. La ejecución requiere una acción separada y,
          en esta fase, solo puede crear borradores de Gmail.
        </div>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Resumen de acción IA">
        <div class="sectionHeader">
          <div>
            <h3>Resumen</h3>
            <p class="sectionText">
              Propuesta generada por el agente. Aprobar registra revisión; la ejecución controlada se hace aparte.
            </p>
          </div>
          <span class="badge status">{{ formatReviewStatus(record.review_status) }}</span>
        </div>
        <dl class="detailGrid">
          <div>
            <dt>Herramienta</dt>
            <dd>{{ formatToolName(record.tool_name) }}</dd>
          </div>
          <div>
            <dt>Proveedor</dt>
            <dd>{{ formatToolProvider(record.provider) }}</dd>
          </div>
          <div>
            <dt>Operación</dt>
            <dd>{{ record.action }}</dd>
          </div>
          <div>
            <dt>Fecha</dt>
            <dd>{{ formatDate(record.created_at) }}</dd>
          </div>
          <div>
            <dt>Resultado ejecución</dt>
            <dd>{{ formatExecutionStatus(record.execution_status) }}</dd>
          </div>
          <div>
            <dt>Ejecutada</dt>
            <dd>{{ formatBooleanYesNo(record.executed) }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel" aria-label="Propuesta del agente">
        <div class="sectionHeader">
          <div>
            <h3>Propuesta del agente</h3>
            <p class="sectionText">Intención detectada y datos propuestos.</p>
          </div>
        </div>
        <dl class="detailGrid singleColumnGrid">
          <div>
            <dt>Conversación</dt>
            <dd>{{ record.conversation_id }}</dd>
          </div>
          <div>
            <dt>Riesgo</dt>
            <dd>{{ formatRiskLevel(record.risk_level) }}</dd>
          </div>
          <div>
            <dt>Requiere aprobación</dt>
            <dd>{{ formatBooleanYesNo(record.requires_approval) }}</dd>
          </div>
        </dl>
        <h3>Objetivo</h3>
        <pre class="jsonBlock">{{ formattedTarget }}</pre>
        <h3>Payload propuesto</h3>
        <pre class="jsonBlock">{{ formattedPayload }}</pre>
      </section>

      <section class="detailPanel" aria-label="Decisión del arnés">
        <div class="sectionHeader">
          <div>
            <h3>Decisión del arnés</h3>
            <p class="sectionText">Resultado de la política de permisos.</p>
          </div>
        </div>
        <dl class="detailGrid singleColumnGrid">
          <div>
            <dt>Decisión</dt>
            <dd>{{ formatToolDecision(record.decision) }}</dd>
          </div>
          <div>
            <dt>Estado de ejecución</dt>
            <dd>{{ formatExecutionStatus(record.execution_status) }}</dd>
          </div>
          <div>
            <dt>Efecto externo</dt>
            <dd>{{ formatBooleanYesNo(record.external_effect) }}</dd>
          </div>
          <div>
            <dt>Regla aplicada</dt>
            <dd>{{ record.metadata?.policy_rule ?? 'Sin dato' }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel fullWidthPanel editPanel" aria-label="Revisión humana">
        <div class="sectionHeader">
          <div>
            <h3>Revisión humana</h3>
            <p class="sectionText">Guarda la decisión operativa. Estos botones no ejecutan Gmail, Calendar, Telegram o WhatsApp.</p>
          </div>
        </div>

        <div class="formGrid">
          <label>
            Estado revisión
            <select v-model="reviewStatus">
              <option v-for="status in TOOL_REVIEW_STATUSES" :key="status" :value="status">
                {{ formatReviewStatus(status) }}
              </option>
            </select>
          </label>

          <label>
            Revisado por
            <input v-model="reviewedBy" placeholder="Nombre o email interno" />
          </label>

          <label class="wideField">
            Notas
            <textarea v-model="reviewerNotes" rows="4" placeholder="Motivo de aprobación, rechazo o dudas pendientes." />
          </label>

          <label class="wideField">
            Payload aprobado opcional
            <textarea v-model="approvedPayloadText" rows="6" spellcheck="false" />
          </label>
        </div>

        <div class="buttonRow">
          <button class="primaryButton" type="button" :disabled="saving" @click="saveReview('approved')">
            Aprobar
          </button>
          <button class="secondaryButton" type="button" :disabled="saving" @click="saveReview('rejected')">
            Rechazar
          </button>
          <button class="secondaryButton" type="button" :disabled="saving" @click="saveReview('needs_more_info')">
            Pedir más información
          </button>
          <button class="secondaryButton" type="button" :disabled="saving" @click="saveReview('dismissed')">
            Descartar
          </button>
          <button class="secondaryButton" type="button" :disabled="saving" @click="saveReview()">
            Guardar
          </button>
        </div>

        <p v-if="saving" class="stateMessage">Guardando revisión...</p>
        <p v-if="savedMessage" class="successMessage">{{ savedMessage }}</p>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Ejecución controlada">
        <div class="sectionHeader">
          <div>
            <h3>Ejecución controlada</h3>
            <p class="sectionText">
              Solo Gmail create_draft y schedule_visit_tool pueden ejecutarse en esta fase, y únicamente si la acción está aprobada.
            </p>
          </div>
        </div>
        <div v-if="canExecute" class="buttonRow">
          <button class="primaryButton" type="button" :disabled="executing" @click="executeAction">
            {{ executeButtonLabel }}
          </button>
          <p class="sectionText">Esto ejecutará la acción en la integración externa correspondiente.</p>
        </div>
        <p v-else class="sectionText">
          Esta acción no está lista para ejecución controlada, ya fue ejecutada o no está aprobada.
        </p>
        <p v-if="executing" class="stateMessage">Ejecutando acción...</p>
        <dl class="detailGrid">
          <div>
            <dt>Ejecutada</dt>
            <dd>{{ formatBooleanYesNo(record.executed) }}</dd>
          </div>
          <div>
            <dt>Fecha ejecución</dt>
            <dd>{{ formatDate(record.executed_at) }}</dd>
          </div>
          <div>
            <dt>Error ejecución</dt>
            <dd>{{ record.execution_error ?? 'Sin dato' }}</dd>
          </div>
        </dl>
        <h3>Resultado seguro de ejecución</h3>
        <pre class="jsonBlock">{{ formattedExecutionResult }}</pre>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Payload aprobado">
        <div class="sectionHeader">
          <div>
            <h3>Payload aprobado</h3>
            <p class="sectionText">Queda auditado para una futura fase de ejecución controlada.</p>
          </div>
        </div>
        <pre class="jsonBlock">{{ formattedApprovedPayload }}</pre>
      </section>

      <details class="detailPanel fullWidthPanel technicalDetails">
        <summary>Datos técnicos</summary>
        <dl class="detailGrid technicalGrid">
          <div>
            <dt>trace_id</dt>
            <dd>{{ record.trace_id }}</dd>
          </div>
          <div>
            <dt>tool_request_id</dt>
            <dd>{{ record.tool_request_id }}</dd>
          </div>
          <div>
            <dt>tool_decision_id</dt>
            <dd>{{ record.tool_decision_id }}</dd>
          </div>
          <div>
            <dt>reviewed_at</dt>
            <dd>{{ formatDate(record.reviewed_at) }}</dd>
          </div>
        </dl>
        <h3>Metadata</h3>
        <pre class="jsonBlock">{{ formattedMetadata }}</pre>
      </details>
    </div>
  </section>
</template>
