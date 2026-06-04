import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Toast } from '../components/dashboard/ToastContainer.vue'

export const useDashboardStore = defineStore('dashboard', () => {
  const filterChannel = ref('all')
  const filterPestType = ref('all')
  const filterPriority = ref('all')
  const lastUpdated = ref('--:--:--')
  const toasts = ref<Toast[]>([])
  const activeIncidentsCount = ref(0)
  const isLoading = ref(false)

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

  function setFilters(channel: string, pestType: string, priority: string) {
    filterChannel.value = channel
    filterPestType.value = pestType
    filterPriority.value = priority
  }

  function setLastUpdated(val: string) {
    lastUpdated.value = val
  }

  function addToast(toast: Toast) {
    toasts.value.push(toast)
  }

  function removeToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function setActiveIncidentsCount(count: number) {
    activeIncidentsCount.value = count
  }

  return {
    filterChannel,
    filterPestType,
    filterPriority,
    lastUpdated,
    toasts,
    activeIncidentsCount,
    isLoading,
    onRefresh,
    removeRefresh,
    triggerRefresh,
    setFilters,
    setLastUpdated,
    addToast,
    removeToast,
    setActiveIncidentsCount
  }
})
