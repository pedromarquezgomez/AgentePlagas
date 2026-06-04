<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string | null | undefined
}>()

const slaLabel = computed(() => {
  if (!props.status) return 'SIN SLA'
  const s = props.status.toUpperCase()
  switch (s) {
    case 'ON_TRACK': return 'En fecha'
    case 'AT_RISK': return 'En riesgo'
    case 'BREACHED': return 'Vencido'
    case 'COMPLETED': return 'Cumplido'
    default: return s
  }
})

const badgeClass = computed(() => {
  if (!props.status) return 'badge'
  const s = props.status.toUpperCase()
  switch (s) {
    case 'ON_TRACK':
    case 'COMPLETED':
      return 'badge sla-on_track'
    case 'AT_RISK':
      return 'badge sla-at_risk'
    case 'BREACHED':
      return 'badge sla-breached'
    default:
      return 'badge'
  }
})
</script>

<template>
  <span :class="badgeClass" style="text-transform: uppercase; font-size: 11px; letter-spacing: 0.03em;">
    {{ slaLabel }}
  </span>
</template>
