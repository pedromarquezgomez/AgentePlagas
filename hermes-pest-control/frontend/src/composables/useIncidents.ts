import { ref, computed } from 'vue'
import {
  fetchIncidents,
  type Incident
} from '../services/api'

export function useIncidents() {
  const incidents = ref<Incident[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const statusFilter = ref('')
  const priorityFilter = ref('')
  const pestTypeFilter = ref('')
  const dispatchBucketFilter = ref('')
  const slaStatusFilter = ref('')
  const incidentSortBy = ref('priority')
  const incidentSortDir = ref<'asc' | 'desc'>('asc')

  const hasFilters = computed(() => {
    return Boolean(
      statusFilter.value ||
      priorityFilter.value ||
      pestTypeFilter.value ||
      dispatchBucketFilter.value ||
      slaStatusFilter.value ||
      incidentSortBy.value !== 'priority' ||
      incidentSortDir.value !== 'asc'
    )
  })

  async function loadIncidents() {
    loading.value = true
    error.value = null
    try {
      incidents.value = await fetchIncidents({
        status: statusFilter.value || undefined,
        priority: priorityFilter.value || undefined,
        pest_type: pestTypeFilter.value || undefined,
        dispatch_bucket: dispatchBucketFilter.value || undefined,
        sla_status: slaStatusFilter.value || undefined,
        sort_by: incidentSortBy.value || undefined,
        sort_dir: incidentSortDir.value || undefined,
        limit: 100
      })
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudieron cargar las incidencias'
      incidents.value = []
    } finally {
      loading.value = false
    }
  }

  function clearFilters() {
    statusFilter.value = ''
    priorityFilter.value = ''
    pestTypeFilter.value = ''
    dispatchBucketFilter.value = ''
    slaStatusFilter.value = ''
    incidentSortBy.value = 'priority'
    incidentSortDir.value = 'asc'
    void loadIncidents()
  }

  function sortIncidents(sortBy: string) {
    if (incidentSortBy.value === sortBy) {
      incidentSortDir.value = incidentSortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      incidentSortBy.value = sortBy
      incidentSortDir.value = sortBy === 'created_at' ? 'desc' : 'asc'
    }
    void loadIncidents()
  }

  return {
    incidents,
    loading,
    error,
    statusFilter,
    priorityFilter,
    pestTypeFilter,
    dispatchBucketFilter,
    slaStatusFilter,
    incidentSortBy,
    incidentSortDir,
    hasFilters,
    loadIncidents,
    clearFilters,
    sortIncidents
  }
}
