import { ref, computed } from 'vue'
import {
  fetchVisits,
  fetchTechnicians,
  type Visit,
  type Technician
} from '../services/api'

export function useVisits() {
  const visits = ref<Visit[]>([])
  const technicians = ref<Technician[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const visitStatusFilter = ref('')
  const visitTechnicianFilter = ref('')

  const hasVisitFilters = computed(() => {
    return Boolean(visitStatusFilter.value || visitTechnicianFilter.value)
  })

  async function loadVisits() {
    loading.value = true
    error.value = null
    try {
      const [loadedVisits, loadedTechnicians] = await Promise.all([
        fetchVisits({
          technician_id: visitTechnicianFilter.value || undefined,
          status: visitStatusFilter.value || undefined,
          limit: 100
        }),
        fetchTechnicians({ active: true, limit: 200 })
      ])
      visits.value = loadedVisits
      technicians.value = loadedTechnicians
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudieron cargar las visitas'
      visits.value = []
    } finally {
      loading.value = false
    }
  }

  function clearVisitFilters() {
    visitStatusFilter.value = ''
    visitTechnicianFilter.value = ''
    void loadVisits()
  }

  return {
    visits,
    technicians,
    loading,
    error,
    visitStatusFilter,
    visitTechnicianFilter,
    hasVisitFilters,
    loadVisits,
    clearVisitFilters
  }
}
