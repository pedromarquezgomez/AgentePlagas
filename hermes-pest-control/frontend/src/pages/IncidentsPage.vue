<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useIncidents } from '../composables/useIncidents'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import IncidentTable from '../components/IncidentTable.vue'
import {
  INCIDENT_STATUSES,
  OPERATIONAL_PRIORITIES,
  PEST_TYPES,
  DISPATCH_BUCKETS,
  SLA_STATUSES
} from '../services/api'
import {
  formatStatus,
  formatPriority,
  formatPestType,
  formatDispatchBucket,
  formatSlaStatus
} from '../utils/labels'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  incidents,
  loading,
  error,
  statusFilter,
  priorityFilter,
  pestTypeFilter,
  dispatchBucketFilter,
  slaStatusFilter,
  hasFilters,
  loadIncidents,
  clearFilters,
  sortIncidents
} = useIncidents()

function openIncident(id: string) {
  void router.push(`/incidents/${encodeURIComponent(id)}`)
}

onMounted(() => {
  void loadIncidents()
  onRefresh(loadIncidents)
})

onUnmounted(() => {
  removeRefresh(loadIncidents)
})
</script>

<template>
  <div class="incidents-page">
    <PageHeader
      title="Historial de Incidencias"
      subtitle="Registro histórico de incidencias de plagas detectadas, su prioridad y estado de SLA."
    />

    <section class="filters" aria-label="Filtros de incidencias">
      <label>
        Estado
        <select v-model="statusFilter" @change="loadIncidents">
          <option value="">Todos</option>
          <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
            {{ formatStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Prioridad
        <select v-model="priorityFilter" @change="loadIncidents">
          <option value="">Todas</option>
          <option v-for="priority in OPERATIONAL_PRIORITIES" :key="priority" :value="priority">
            {{ formatPriority(priority) }}
          </option>
        </select>
      </label>

      <label>
        Plaga
        <select v-model="pestTypeFilter" @change="loadIncidents">
          <option value="">Todas</option>
          <option v-for="pestType in PEST_TYPES" :key="pestType" :value="pestType">
            {{ formatPestType(pestType) }}
          </option>
        </select>
      </label>

      <label>
        Cola
        <select v-model="dispatchBucketFilter" @change="loadIncidents">
          <option value="">Todas</option>
          <option v-for="bucket in DISPATCH_BUCKETS" :key="bucket" :value="bucket">
            {{ formatDispatchBucket(bucket) }}
          </option>
        </select>
      </label>

      <label>
        SLA
        <select v-model="slaStatusFilter" @change="loadIncidents">
          <option value="">Todos</option>
          <option v-for="slaStatus in SLA_STATUSES" :key="slaStatus" :value="slaStatus">
            {{ formatSlaStatus(slaStatus) }}
          </option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasFilters" @click="clearFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loading" message="Cargando incidencias..." />
      <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
      <EmptyState v-else-if="incidents.length === 0" message="No hay incidencias para los filtros seleccionados." />
      <IncidentTable v-else :incidents="incidents" @open="openIncident" @sort="sortIncidents" />
    </section>
  </div>
</template>

<style scoped>
.incidents-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
