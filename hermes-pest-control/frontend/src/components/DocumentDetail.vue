<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  DOCUMENT_STATUSES,
  fetchDocument,
  isUnauthorizedError,
  updateDocument,
  type OperationalDocument,
  type OperationalDocumentStatus,
} from '../services/api'

const props = defineProps<{
  documentId: string
}>()

const emit = defineEmits<{
  back: []
  unauthorized: []
}>()

const documentData = ref<OperationalDocument | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const formTitle = ref('')
const formContent = ref('')
const formStatus = ref<OperationalDocumentStatus>('draft')

function isDocumentStatus(value: string): value is OperationalDocumentStatus {
  return DOCUMENT_STATUSES.includes(value as OperationalDocumentStatus)
}

function syncForm(document: OperationalDocument): void {
  formTitle.value = document.title
  formContent.value = document.content
  formStatus.value = isDocumentStatus(document.status) ? document.status : 'draft'
}

async function loadDocument(): Promise<void> {
  loading.value = true
  error.value = null
  saveError.value = null
  saveSuccess.value = false

  try {
    const loadedDocument = await fetchDocument(props.documentId)
    documentData.value = loadedDocument
    syncForm(loadedDocument)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar el documento'
    documentData.value = null
  } finally {
    loading.value = false
  }
}

async function saveDocument(): Promise<void> {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  try {
    await updateDocument(props.documentId, {
      title: formTitle.value.trim(),
      content: formContent.value,
      status: formStatus.value,
    })
    const refreshedDocument = await fetchDocument(props.documentId)
    documentData.value = refreshedDocument
    syncForm(refreshedDocument)
    saveSuccess.value = true
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar el documento'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.documentId,
  () => {
    void loadDocument()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">Detalle de documento</p>
        <h2>{{ documentData?.title ?? 'Documento' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando documento...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <form v-else-if="documentData" class="editPanel widePanel" aria-label="Guardar documento" @submit.prevent="saveDocument">
      <label>
        Título
        <input v-model="formTitle" :disabled="saving" required type="text" />
      </label>

      <label>
        Estado
        <select v-model="formStatus" :disabled="saving">
          <option v-for="status in DOCUMENT_STATUSES" :key="status" :value="status">
            {{ status }}
          </option>
        </select>
      </label>

      <label>
        Contenido
        <textarea v-model="formContent" :disabled="saving" rows="18" />
      </label>

      <div class="formActions">
        <button class="primaryButton" type="submit" :disabled="saving || !formTitle.trim()">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
        <span v-if="saveSuccess" class="saveMessage">Guardado correctamente.</span>
      </div>

      <div v-if="saveError" class="stateMessage errorMessage">{{ saveError }}</div>
    </form>
  </section>
</template>
