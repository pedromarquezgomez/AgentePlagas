<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useVisits } from '../composables/useVisits'
import {
  fetchIncidents,
  updateVisit,
  isUnauthorizedError,
  type VisitStatus,
  type Incident,
  type Technician,
  VISIT_STATUSES,
} from '../services/api'
import { formatStatus } from '../utils/labels'

import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import VisitKanban from '../components/dashboard/VisitKanban.vue'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  visits,
  technicians,
  loading: loadingVisits,
  error: visitsError,
  visitStatusFilter,
  visitTechnicianFilter,
  hasVisitFilters,
  loadVisits,
  clearVisitFilters
} = useVisits()

const incidents = ref<Incident[]>([])
const loadingIncidents = ref(false)
const localError = ref<string | null>(null)

// Cargar incidentes
async function loadIncidentsData() {
  loadingIncidents.value = true
  try {
    incidents.value = await fetchIncidents({ limit: 500 })
  } catch (err) {
    console.error('Error cargando incidencias en visitas:', err)
  } finally {
    loadingIncidents.value = false
  }
}

// Mapa de incidentes para acceso rápido
const incidentsMap = computed(() => {
  const map: Record<string, Incident> = {}
  incidents.value.forEach(inc => {
    map[inc.id] = inc
  })
  return map
})

// Mapa de técnicos para acceso rápido
const techniciansMap = computed(() => {
  const map: Record<string, Technician> = {}
  technicians.value.forEach(tech => {
    map[tech.id] = tech
  })
  return map
})

async function refreshAll() {
  localError.value = null
  await Promise.all([
    loadVisits(),
    loadIncidentsData()
  ])
}

// Acciones del Kanban
async function handleUpdateStatus(visitId: string, status: VisitStatus) {
  localError.value = null
  try {
    await updateVisit(visitId, { status })
    await loadVisits()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      void router.push('/login')
      return
    }
    localError.value = err instanceof Error ? err.message : 'No se pudo actualizar el estado de la visita'
  }
}

async function handleUpdateTechnician(visitId: string, technicianId: string | null) {
  localError.value = null
  try {
    await updateVisit(visitId, { technician_id: technicianId })
    await loadVisits()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      void router.push('/login')
      return
    }
    localError.value = err instanceof Error ? err.message : 'No se pudo reasignar el técnico'
  }
}

function openVisit(id: string) {
  void router.push(`/visits/${encodeURIComponent(id)}`)
}

function openNewVisit() {
  void router.push('/visits/new')
}

onMounted(() => {
  void refreshAll()
  onRefresh(refreshAll)
})

onUnmounted(() => {
  removeRefresh(refreshAll)
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

    <!-- Filtros de Visitas -->
    <section class="filters" aria-label="Filtros de visitas">
      <label>
        Estado visita
        <select v-model="visitStatusFilter" @change="loadVisits">
          <option value="">Todos los estados</option>
          <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
            {{ formatStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Técnico asignado
        <select v-model="visitTechnicianFilter" @change="loadVisits">
          <option value="">Todos los técnicos</option>
          <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
            {{ technician.name }}
          </option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasVisitFilters" @click="clearVisitFilters">
        Limpiar Filtros
      </button>
    </section>

    <!-- Kanban Board -->
    <section class="contentBand">
      <LoadingState v-if="loadingVisits || loadingIncidents" message="Cargando visitas operativas..." />
      <ErrorBanner v-else-if="visitsError || localError" :error="visitsError || localError" @dismiss="localError = null" />
      
      <!-- Kanban component -->
      <VisitKanban
        v-else
        :visits="visits"
        :incidentsMap="incidentsMap"
        :techniciansMap="techniciansMap"
        :allTechnicians="technicians"
        @open="openVisit"
        @updateStatus="handleUpdateStatus"
        @updateTechnician="handleUpdateTechnician"
        @createVisit="openNewVisit"
      />
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
