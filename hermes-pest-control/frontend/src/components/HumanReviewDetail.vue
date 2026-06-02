<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  fetchHumanReviewItem,
  HUMAN_REVIEW_STATUSES,
  isUnauthorizedError,
  updateHumanReviewItem,
  type HumanReviewItem,
  type HumanReviewStatus,
} from '../services/api'
import { formatReason, formatStatus } from '../utils/labels'

const props = defineProps<{
  itemId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const item = ref<HumanReviewItem | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const formStatus = ref<HumanReviewStatus>('open')
const formAssignedTo = ref('')
const formResolutionNotes = ref('')

function formatValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function isHumanReviewStatus(value: string): value is HumanReviewStatus {
  return HUMAN_REVIEW_STATUSES.includes(value as HumanReviewStatus)
}

function syncForm(nextItem: HumanReviewItem): void {
  if (isHumanReviewStatus(nextItem.status)) {
    formStatus.value = nextItem.status
  }
  formAssignedTo.value = nextItem.assigned_to ?? ''
  formResolutionNotes.value = nextItem.resolution_notes ?? ''
}

async function loadItem(): Promise<void> {
  loading.value = true
  error.value = null
  saveError.value = null
  saveSuccess.value = false

  try {
    const loadedItem = await fetchHumanReviewItem(props.itemId)
    item.value = loadedItem
    syncForm(loadedItem)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la revisión'
    item.value = null
  } finally {
    loading.value = false
  }
}

async function saveItem(): Promise<void> {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  try {
    await updateHumanReviewItem(props.itemId, {
      status: formStatus.value,
      assigned_to: formAssignedTo.value,
      resolution_notes: formResolutionNotes.value,
    })
    const refreshedItem = await fetchHumanReviewItem(props.itemId)
    item.value = refreshedItem
    syncForm(refreshedItem)
    saveSuccess.value = true
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar la revisión'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.itemId,
  () => {
    void loadItem()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">Detalle de revisión humana</p>
        <h2>{{ item ? formatReason(item.reason) : 'Revisión humana' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando revisión...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <div v-else-if="item" class="detailLayout">
      <section class="detailPanel" aria-label="Datos de la revisión humana">
        <dl class="detailGrid">
          <div>
            <dt>Razón</dt>
            <dd>{{ item.reason }}</dd>
          </div>
          <div>
            <dt>Prioridad</dt>
            <dd>
              <span class="badge" :class="`priority-${item.priority}`">
                {{ item.priority }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd><span class="badge status">{{ item.status }}</span></dd>
          </div>
          <div>
            <dt>Canal</dt>
            <dd>{{ item.channel }}</dd>
          </div>
          <div>
            <dt>Incidencia</dt>
            <dd>{{ formatValue(item.incident_id) }}</dd>
          </div>
          <div>
            <dt>Decision record</dt>
            <dd>{{ formatValue(item.decision_record_id) }}</dd>
          </div>
          <div>
            <dt>Conversación</dt>
            <dd>{{ item.conversation_id }}</dd>
          </div>
          <div>
            <dt>Trace</dt>
            <dd>{{ item.trace_id }}</dd>
          </div>
          <div>
            <dt>Fecha creación</dt>
            <dd>{{ formatDate(item.created_at) }}</dd>
          </div>
          <div>
            <dt>Fecha resolución</dt>
            <dd>{{ formatDate(item.resolved_at) }}</dd>
          </div>
        </dl>

        <div class="summaryBlock">
          <h3>Resumen</h3>
          <p>{{ formatValue(item.summary) }}</p>
        </div>
      </section>

      <form class="editPanel" aria-label="Actualizar revisión humana" @submit.prevent="saveItem">
        <label>
          Estado
          <select v-model="formStatus" :disabled="saving">
            <option v-for="status in HUMAN_REVIEW_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Asignado a
          <input
            v-model="formAssignedTo"
            :disabled="saving"
            placeholder="Nombre o equipo responsable"
            type="text"
          />
        </label>

        <label>
          Notas de resolución
          <textarea
            v-model="formResolutionNotes"
            :disabled="saving"
            placeholder="Decisión tomada por el equipo"
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
