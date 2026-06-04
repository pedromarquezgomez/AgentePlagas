<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGlobalState } from '../composables/useGlobalState'
import { useDocuments } from '../composables/useDocuments'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import DocumentTable from '../components/DocumentTable.vue'
import { formatDocumentType, formatStatus } from '../utils/labels'

const router = useRouter()
const { onRefresh, removeRefresh } = useGlobalState()
const {
  documents,
  loading,
  error,
  documentTypeFilter,
  documentStatusFilter,
  hasDocumentFilters,
  loadDocuments,
  clearDocumentFilters
} = useDocuments()

const DOCUMENT_TYPE_OPTIONS = [
  'incident_summary',
  'technician_brief',
  'post_treatment_recommendations',
  'work_report_draft'
] as const

function openDocument(id: string) {
  void router.push(`/documents/${encodeURIComponent(id)}`)
}

onMounted(() => {
  void loadDocuments()
  onRefresh(loadDocuments)
})

onUnmounted(() => {
  removeRefresh(loadDocuments)
})
</script>

<template>
  <div class="documents-page">
    <PageHeader
      title="Repositorio de Documentos"
      subtitle="Listado y consulta de reportes, briefings y sumarios de tratamiento emitidos."
    />

    <section class="filters" aria-label="Filtros de documentos">
      <label>
        Tipo
        <select v-model="documentTypeFilter" @change="loadDocuments">
          <option value="">Todos</option>
          <option v-for="type in DOCUMENT_TYPE_OPTIONS" :key="type" :value="type">
            {{ formatDocumentType(type) }}
          </option>
        </select>
      </label>

      <label>
        Estado
        <select v-model="documentStatusFilter" @change="loadDocuments">
          <option value="">Todos</option>
          <option value="draft">{{ formatStatus('draft') }}</option>
          <option value="reviewed">{{ formatStatus('reviewed') }}</option>
          <option value="archived">{{ formatStatus('archived') }}</option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasDocumentFilters" @click="clearDocumentFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loading" message="Cargando documentos..." />
      <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
      <EmptyState v-else-if="documents.length === 0" message="No hay documentos para los filtros seleccionados." />
      <DocumentTable v-else :documents="documents" @open="openDocument" />
    </section>
  </div>
</template>

<style scoped>
.documents-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
