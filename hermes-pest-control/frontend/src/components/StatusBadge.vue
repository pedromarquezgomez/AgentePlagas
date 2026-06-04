<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  type?: 'incident' | 'tool' | 'generic'
}>()

const formattedLabel = computed(() => {
  const s = props.status.toLowerCase()
  switch (s) {
    // Incident statuses
    case 'new': return 'Nuevo'
    case 'pending_review': return 'Pendiente revisión'
    case 'waiting_for_client_data': return 'Esperando datos'
    case 'ready_for_scheduling': return 'Listo para agendar'
    case 'scheduled': return 'Agendado'
    case 'in_progress': return 'En curso'
    case 'completed': return 'Completado'
    case 'follow_up_pending': return 'Seguimiento pendiente'
    case 'closed': return 'Cerrado'
    case 'cancelled': return 'Cancelado'
    
    // Tool statuses
    case 'proposed': return 'Propuesto'
    case 'approved': return 'Aprobado'
    case 'rejected': return 'Rechazado'
    case 'needs_more_info': return 'Falta información'
    case 'dismissed': return 'Descartado'

    default: return props.status
  }
})

const badgeClass = computed(() => {
  const s = props.status.toLowerCase()
  switch (s) {
    case 'new':
    case 'pending_review':
    case 'proposed':
      return 'badge status-pending'
    case 'in_progress':
    case 'ready_for_scheduling':
      return 'badge status'
    case 'completed':
    case 'closed':
    case 'approved':
      return 'badge agreement-ok'
    case 'cancelled':
    case 'rejected':
    case 'dismissed':
      return 'badge agreement-error'
    case 'waiting_for_client_data':
    case 'needs_more_info':
      return 'badge agreement-warning'
    default:
      return 'badge'
  }
})

const customStyles = computed(() => {
  const s = props.status.toLowerCase()
  switch (s) {
    case 'proposed':
      return { background: '#fffbeb', color: '#b45309', border: '1px solid #fef3c7' }
    case 'pending_review':
      return { background: '#f3f4f6', color: '#374151', border: '1px solid #e5e7eb' }
    default:
      return {}
  }
})
</script>

<template>
  <span :class="badgeClass" :style="customStyles" style="text-transform: uppercase; font-size: 11px; letter-spacing: 0.03em;">
    {{ formattedLabel }}
  </span>
</template>
