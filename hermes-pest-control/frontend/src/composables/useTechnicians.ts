import { ref, computed } from 'vue'
import {
  fetchTechnicians,
  type Technician
} from '../services/api'

export function useTechnicians() {
  const technicians = ref<Technician[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const technicianActiveFilter = ref('')

  const hasTechnicianFilters = computed(() => {
    return Boolean(technicianActiveFilter.value)
  })

  async function loadTechnicians() {
    loading.value = true
    error.value = null
    try {
      technicians.value = await fetchTechnicians({
        active: technicianActiveFilter.value === '' ? undefined : technicianActiveFilter.value === 'true',
        limit: 100
      })
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'No se pudieron cargar los técnicos'
      technicians.value = []
    } finally {
      loading.value = false
    }
  }

  function clearTechnicianFilters() {
    technicianActiveFilter.value = ''
    void loadTechnicians()
  }

  return {
    technicians,
    loading,
    error,
    technicianActiveFilter,
    hasTechnicianFilters,
    loadTechnicians,
    clearTechnicianFilters
  }
}
