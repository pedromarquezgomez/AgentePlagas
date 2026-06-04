<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useTechnicians } from '../composables/useTechnicians'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import TechnicianTable from '../components/TechnicianTable.vue'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  technicians,
  loading,
  error,
  technicianActiveFilter,
  hasTechnicianFilters,
  loadTechnicians,
  clearTechnicianFilters
} = useTechnicians()

function openTechnician(id: string) {
  void router.push(`/technicians/${encodeURIComponent(id)}`)
}

function openNewTechnician() {
  void router.push('/technicians/new')
}

onMounted(() => {
  void loadTechnicians()
  onRefresh(loadTechnicians)
})

onUnmounted(() => {
  removeRefresh(loadTechnicians)
})
</script>

<template>
  <div class="technicians-page">
    <div class="sectionHeader">
      <PageHeader
        title="Técnicos de Servicio"
        subtitle="Listado y estado de disponibilidad del personal técnico asignado."
      />
      <button class="primaryButton" type="button" @click="openNewTechnician">
        Nuevo técnico
      </button>
    </div>

    <section class="filters" aria-label="Filtros de técnicos">
      <label>
        Activo
        <select v-model="technicianActiveFilter" @change="loadTechnicians">
          <option value="">Todos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasTechnicianFilters" @click="clearTechnicianFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loading" message="Cargando técnicos..." />
      <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
      <EmptyState v-else-if="technicians.length === 0" message="No hay técnicos para los filtros seleccionados." />
      <TechnicianTable v-else :technicians="technicians" @open="openTechnician" />
    </section>
  </div>
</template>

<style scoped>
.technicians-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
