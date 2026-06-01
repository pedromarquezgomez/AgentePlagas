<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  getShadowDecisionRecord,
  isUnauthorizedError,
  type ShadowDecisionRecord,
} from '../services/api'

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

function formatValue(value: string | boolean | null | undefined): string {
  if (typeof value === 'boolean') return value ? 'sí' : 'no'
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
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la decisión shadow'
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
        <p class="eyebrow">Detalle de evaluación LLM</p>
        <h2>{{ record ? record.conversation_id : 'Shadow Decision' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando decisión shadow...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <div v-else-if="record" class="detailLayout">
      <section class="detailPanel fullWidthPanel" aria-label="Comparación shadow">
        <dl class="detailGrid">
          <div>
            <dt>Trace</dt>
            <dd>{{ record.trace_id }}</dd>
          </div>
          <div>
            <dt>Conversación</dt>
            <dd>{{ record.conversation_id }}</dd>
          </div>
          <div>
            <dt>Canal</dt>
            <dd>{{ record.channel }}</dd>
          </div>
          <div>
            <dt>Fecha</dt>
            <dd>{{ formatDate(record.created_at) }}</dd>
          </div>
          <div>
            <dt>Primary Hermes</dt>
            <dd>{{ record.primary_hermes_mode }}</dd>
          </div>
          <div>
            <dt>Shadow Hermes</dt>
            <dd>{{ record.shadow_hermes_mode }}</dd>
          </div>
          <div>
            <dt>Primary action</dt>
            <dd>{{ record.primary_action_type }}</dd>
          </div>
          <div>
            <dt>Shadow action</dt>
            <dd>{{ formatValue(record.shadow_action_type) }}</dd>
          </div>
          <div>
            <dt>Primary priority</dt>
            <dd>{{ formatValue(record.primary_priority) }}</dd>
          </div>
          <div>
            <dt>Shadow priority</dt>
            <dd>{{ formatValue(record.shadow_priority) }}</dd>
          </div>
          <div>
            <dt>Primary pest</dt>
            <dd>{{ formatValue(record.primary_pest_type) }}</dd>
          </div>
          <div>
            <dt>Shadow pest</dt>
            <dd>{{ formatValue(record.shadow_pest_type) }}</dd>
          </div>
          <div>
            <dt>Primary should create</dt>
            <dd>{{ formatValue(record.primary_should_create) }}</dd>
          </div>
          <div>
            <dt>Shadow should create</dt>
            <dd>{{ formatValue(record.shadow_should_create) }}</dd>
          </div>
          <div>
            <dt>Agreement</dt>
            <dd>{{ record.agreement_summary }}</dd>
          </div>
          <div>
            <dt>Shadow fallback</dt>
            <dd>{{ formatValue(record.shadow_fallback_used) }}</dd>
          </div>
          <div>
            <dt>Shadow error</dt>
            <dd>{{ formatValue(record.shadow_error) }}</dd>
          </div>
        </dl>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Diferencias">
        <div class="sectionHeader">
          <div>
            <h3>Diferencias</h3>
            <p class="sectionText">Comparación estructurada entre la decisión primaria y shadow.</p>
          </div>
        </div>
        <pre class="jsonBlock">{{ formattedDifferences }}</pre>
      </section>

      <section class="detailPanel fullWidthPanel" aria-label="Metadata">
        <div class="sectionHeader">
          <div>
            <h3>Metadata</h3>
            <p class="sectionText">Datos operativos asociados al registro.</p>
          </div>
        </div>
        <pre class="jsonBlock">{{ formattedMetadata }}</pre>
      </section>
    </div>
  </section>
</template>
