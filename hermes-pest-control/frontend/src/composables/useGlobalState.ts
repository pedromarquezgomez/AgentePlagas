import { ref } from 'vue'
import type { Toast } from '../components/dashboard/ToastContainer.vue'

const filterChannel = ref('all')
const filterPestType = ref('all')
const filterPriority = ref('all')
const isLoading = ref(false)
const lastUpdated = ref('--:--:--')
const toasts = ref<Toast[]>([])
const activeIncidentsCount = ref(0)

const refreshCallbacks = new Set<() => void | Promise<void>>()

function onRefresh(cb: () => void | Promise<void>) {
  refreshCallbacks.add(cb)
}

function removeRefresh(cb: () => void | Promise<void>) {
  refreshCallbacks.delete(cb)
}

async function triggerRefresh() {
  isLoading.value = true
  const promises = Array.from(refreshCallbacks).map(cb => {
    try {
      return cb()
    } catch (e) {
      console.error('Error in refresh callback:', e)
    }
  })
  await Promise.all(promises)
  isLoading.value = false
  lastUpdated.value = new Date().toTimeString().split(' ')[0]
}

export function useGlobalState() {
  return {
    filterChannel,
    filterPestType,
    filterPriority,
    isLoading,
    lastUpdated,
    toasts,
    activeIncidentsCount,
    onRefresh,
    removeRefresh,
    triggerRefresh
  }
}
