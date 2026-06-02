<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  getShadowDecisionRecord,
  isUnauthorizedError,
  type ShadowDecisionRecord,
} from '../services/api'
import {
  agreementClass,
  differenceText,
  formatAction,
  formatAgreement,
  formatBooleanYesNo,
  formatChannel,
  formatFallback,
  formatHermesMode,
  formatPlainValue,
  formatPriority,
  normalizeDifferences,
  shadowInterpretation,
} from '../utils/labels'

const props = defineProps<{
  recordId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const record = ref<ShadowDecisionRecord | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const formattedDifferences = computed(() => formatJson(record.value?.differences))
const formattedMetadata = computed(() => formatJson(record.value?.metadata))
const differences = computed(() => normalizeDifferences(record.value?.differences))

function formatDate(value: string | undefined): string {
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

async function loadRecord(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    record.value = await getShadowDecisionRecord(props.recordId)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la evaluación IA'
    record.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.recordId,
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
        <p class="eyebrow">Detalle de evaluación IA</p>
        <h2>{{ record ? record.conversation_id : 'Comparativa IA' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando evaluación IA...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <div v-else-if="record" class="detailLayout">
      <section class="detailPanel fullWidthPanel" aria-label="Resumen de evaluación IA">
        <div class="sectionHeader">
          <div>
            <h3>Resumen</h3>
            <p class="sectionText">{{ shadowInterpretation(record.agreement_summary) }}</p>
          </div>
          <span class="badge" :class="agreementClass(record.agreement_summary)">
            {{ formatAgreement(record.agreement_summary) }}
          </span>
        </div>
        <dl class="detailGrid">
          <div>
            <dt>¿Coinciden?</dt>
            <dd>{{ formatAgreement(record.agreement_summary) }}</dd>
          </div>
          <div>
            <dt>¿Hubo error?</dt>
            <dd>{{ record.shadow_error ? 'Sí' : 'No' }}</dd>
          </div>
          <div>
            <dt>¿Se usó respuesta segura?</dt>
            <dd>{{ formatFallback(record.shadow_fallback_used) }}</dd>
          </div>
          <div>
            <dt>Fecha</dt>
            <dd>{{ formatDate(record.created_at) }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel" aria-label="Sistema actual">
        <div class="sectionHeader">
          <div>
            <h3>Sistema actual</h3>
            <p class="sectionText">Decisión que sí se usó para responder y operar.</p>
          </div>
        </div>
        <dl class="detailGrid singleColumnGrid">
          <div>
            <dt>Modo</dt>
            <dd>{{ formatHermesMode(record.primary_hermes_mode) }}</dd>
          </div>
          <div>
            <dt>Acción</dt>
            <dd>{{ formatAction(record.primary_action_type) }}</dd>
          </div>
          <div>
            <dt>Prioridad</dt>
            <dd>{{ formatPriority(record.primary_priority) }}</dd>
          </div>
          <div>
            <dt>Plaga</dt>
            <dd>{{ formatPlainValue(record.primary_pest_type) }}</dd>
          </div>
          <div>
            <dt>¿Crear incidencia?</dt>
            <dd>{{ formatBooleanYesNo(record.primary_should_create) }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel" aria-label="IA en sombra">
        <div class="sectionHeader">
          <div>
            <h3>IA en sombra</h3>
            <p class="sectionText">Decisión simulada. No respondió al cliente ni ejecutó acciones reales.</p>
          </div>
        </div>
        <dl class="detailGrid singleColumnGrid">
          <div>
            <dt>Modo</dt>
            <dd>{{ formatHermesMode(record.shadow_hermes_mode) }}</dd>
          </div>
          <div>
            <dt>Acción propuesta</dt>
            <dd>{{ formatAction(record.shadow_action_type) }}</dd>
          </div>
          <div>
            <dt>Prioridad propuesta</dt>
            <dd>{{ formatPriority(record.shadow_priority) }}</dd>
          </div>
          <div>
            <dt>Plaga detectada</dt>
            <dd>{{ formatPlainValue(record.shadow_pest_type) }}</dd>
          </div>
          <div>
            <dt>¿Crearía incidencia?</dt>
            <dd>{{ formatBooleanYesNo(record.shadow_should_create) }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Diferencias detectadas">
        <div class="sectionHeader">
          <div>
            <h3>Diferencias detectadas</h3>
            <p class="sectionText">Lectura en lenguaje natural de la comparación.</p>
          </div>
        </div>
        <ul v-if="differences.length" class="differenceList">
          <li v-for="difference in differences" :key="difference">
            {{ differenceText(difference) }}
          </li>
        </ul>
        <p v-else class="sectionText">Ambos coinciden.</p>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Interpretación">
        <div class="sectionHeader">
          <div>
            <h3>Interpretación</h3>
            <p class="sectionText">{{ shadowInterpretation(record.agreement_summary) }}</p>
          </div>
        </div>
      </section>

      <details class="detailPanel fullWidthPanel technicalDetails">
        <summary>Datos técnicos</summary>
        <dl class="detailGrid technicalGrid">
          <div>
            <dt>trace_id</dt>
            <dd>{{ record.trace_id }}</dd>
          </div>
          <div>
            <dt>conversation_id</dt>
            <dd>{{ record.conversation_id }}</dd>
          </div>
          <div>
            <dt>Canal</dt>
            <dd>{{ formatChannel(record.channel) }}</dd>
          </div>
          <div>
            <dt>primary_hermes_mode</dt>
            <dd>{{ record.primary_hermes_mode }}</dd>
          </div>
          <div>
            <dt>shadow_hermes_mode</dt>
            <dd>{{ record.shadow_hermes_mode }}</dd>
          </div>
        </dl>
        <h3>Diferencias crudas</h3>
        <pre class="jsonBlock">{{ formattedDifferences }}</pre>
        <h3>Metadata</h3>
        <pre class="jsonBlock">{{ formattedMetadata }}</pre>
      </details>
    </div>
  </section>
</template>
