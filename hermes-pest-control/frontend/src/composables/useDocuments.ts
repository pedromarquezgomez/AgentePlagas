import { ref, computed } from 'vue'
import {
  fetchDocuments,
  type OperationalDocument,
  type OperationalDocumentStatus
} from '../services/api'

export function useDocuments() {
  const documents = ref<OperationalDocument[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  const documentTypeFilter = ref('')
  const documentStatusFilter = ref('')

  const hasDocumentFilters = computed(() => {
    return Boolean(documentTypeFilter.value || documentStatusFilter.value)
  })

  async function loadDocuments() {
    loading.value = true
    error.value = null
    try {
      documents.value = await fetchDocuments({
        document_type: documentTypeFilter.value || undefined,
        status: documentStatusFilter.value || undefined,
        limit: 100
      })
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudieron cargar los documentos'
      documents.value = []
    } finally {
      loading.value = false
    }
  }

  function clearDocumentFilters() {
    documentTypeFilter.value = ''
    documentStatusFilter.value = ''
    void loadDocuments()
  }

  return {
    documents,
    loading,
    error,
    documentTypeFilter,
    documentStatusFilter,
    hasDocumentFilters,
    loadDocuments,
    clearDocumentFilters
  }
}
