<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useVisits } from '../composables/useVisits'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import VisitTable from '../components/VisitTable.vue'
import { VISIT_STATUSES } from '../services/api'
import { formatStatus } from '../utils/labels'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  visits,
  technicians,
  loading,
  error,
  visitStatusFilter,
  visitTechnicianFilter,
  hasVisitFilters,
  loadVisits,
  clearVisitFilters
} = useVisits()

function openVisit(id: string) {
  void router.push(`/visits/${encodeURIComponent(id)}`)
}

function openNewVisit() {
  void router.push('/visits/new')
}

onMounted(() => {
  void loadVisits()
  onRefresh(loadVisits)
})

onUnmounted(() => {
  removeRefresh(loadVisits)
})
</script>

<template>
  <div class="visits-page">
    <div class="sectionHeader">
      <PageHeader
        title="Planificación de Visitas"
        subtitle="Visitas técnicas programadas y asignaciones de tratamiento sobre el terreno."
      />
      <button class="primaryButton" type="button" @click="openNewVisit">
        Nueva visita
      </button>
    </div>

    <section class="filters" aria-label="Filtros de visitas">
      <label>
        Estado
        <select v-model="visitStatusFilter" @change="loadVisits">
          <option value="">Todos</option>
          <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
            {{ formatStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Técnico
        <select v-model="visitTechnicianFilter" @change="loadVisits">
          <option value="">Todos</option>
          <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
            {{ technician.name }}
          </option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasVisitFilters" @click="clearVisitFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loading" message="Cargando visitas..." />
      <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
      <EmptyState v-else-if="visits.length === 0" message="No hay visitas para los filtros seleccionados." />
      <VisitTable v-else :visits="visits" @open="openVisit" />
    </section>
  </div>
</template>

<style scoped>
.visits-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
