<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import { useToolExecutions } from '../composables/useToolExecutions'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import HumanReviewTable from '../components/HumanReviewTable.vue'
import { HUMAN_REVIEW_STATUSES, INCIDENT_PRIORITIES } from '../services/api'
import { formatStatus, formatPriority } from '../utils/labels'

const router = useRouter()
const store = useDashboardStore()
const { onRefresh, removeRefresh } = store
const {
  reviewItems,
  reviewStatusFilter,
  reviewPriorityFilter,
  loadingReviews,
  errorReviews,
  hasReviewFilters,
  loadHumanReviewItems,
  clearReviewFilters
} = useToolExecutions()

function openHumanReview(id: string) {
  void router.push(`/reviews/${encodeURIComponent(id)}`)
}

onMounted(() => {
  void loadHumanReviewItems()
  onRefresh(loadHumanReviewItems)
})

onUnmounted(() => {
  removeRefresh(loadHumanReviewItems)
})
</script>

<template>
  <div class="human-review-page">
    <PageHeader
      title="Cola de Revisión Humana (HITL)"
      subtitle="Intervenciones y aprobaciones manuales pendientes para control del agente."
    />

    <section class="filters" aria-label="Filtros de revisión humana">
      <label>
        Estado
        <select v-model="reviewStatusFilter" @change="loadHumanReviewItems">
          <option value="">Todos</option>
          <option v-for="status in HUMAN_REVIEW_STATUSES" :key="status" :value="status">
            {{ formatStatus(status) }}
          </option>
        </select>
      </label>

      <label>
        Prioridad
        <select v-model="reviewPriorityFilter" @change="loadHumanReviewItems">
          <option value="">Todas</option>
          <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
            {{ formatPriority(priority) }}
          </option>
        </select>
      </label>

      <button class="secondaryButton" type="button" :disabled="!hasReviewFilters" @click="clearReviewFilters">
        Limpiar
      </button>
    </section>

    <section class="contentBand">
      <LoadingState v-if="loadingReviews" message="Cargando revisión humana..." />
      <ErrorBanner v-else-if="errorReviews" :error="errorReviews" @dismiss="errorReviews = null" />
      <EmptyState v-else-if="reviewItems.length === 0" message="No hay elementos de revisión para los filtros seleccionados." />
      <HumanReviewTable v-else :items="reviewItems" @open="openHumanReview" />
    </section>
  </div>
</template>

<style scoped>
.human-review-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
