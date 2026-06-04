<script setup lang="ts">
import { computed } from 'vue'
import { formatSlaStatus } from '../../utils/labels'

const props = defineProps<{
  slaStatus: string
  remainingHours?: number | null
  breachHours?: number | null
}>()

const slaLabel = computed(() => formatSlaStatus(props.slaStatus))

const variantClass = computed(() => {
  const s = props.slaStatus.toUpperCase()
  if (s === 'BREACHED') return 'sla-breached'
  if (s === 'AT_RISK') return 'sla-at-risk'
  if (s === 'ON_TRACK' || s === 'COMPLETED') return 'sla-on-track'
  return 'sla-default'
})
</script>

<template>
  <span class="sla-badge" :class="variantClass">
    <span class="sla-dot"></span>
    <span class="sla-text-container">
      <span class="sla-label">{{ slaLabel }}</span>
      <span v-if="slaStatus === 'BREACHED' && breachHours !== undefined && breachHours !== null" class="sla-time">
        (+{{ breachHours }}h)
      </span>
      <span v-else-if="slaStatus !== 'BREACHED' && remainingHours !== undefined && remainingHours !== null" class="sla-time">
        ({{ remainingHours }}h rest.)
      </span>
    </span>
  </span>
</template>

<style scoped>
.sla-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.sla-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sla-text-container {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sla-label {
  font-weight: 700;
}

.sla-time {
  font-size: 10px;
  color: #71717a;
  font-weight: 400;
}

/* On Track / Completed */
.sla-on-track .sla-dot {
  background: #10b981;
}
.sla-on-track .sla-label {
  color: #34d399;
}

/* At Risk */
.sla-at-risk .sla-dot {
  background: #f59e0b;
  animation: pulse 2s infinite;
}
.sla-at-risk .sla-label {
  color: #fbbf24;
}

/* Breached */
.sla-breached .sla-dot {
  background: #ef4444;
  animation: pulse 1.5s infinite;
}
.sla-breached .sla-label {
  color: #f87171;
}

/* Default */
.sla-default .sla-dot {
  background: #71717a;
}
.sla-default .sla-label {
  color: #a1a1aa;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.6;
  }
}
</style>
