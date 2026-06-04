<script setup lang="ts">
import { computed } from 'vue'
import { formatSeverity, formatPriority } from '../../utils/labels'

const props = defineProps<{
  priority?: string | null
  severity?: string | null
}>()

const severityLabel = computed(() => props.severity ? formatSeverity(props.severity) : '')
const priorityLabel = computed(() => props.priority ? formatPriority(props.priority) : '')

const severityClass = computed(() => {
  if (!props.severity) return ''
  const s = props.severity.toUpperCase()
  if (s === 'CRITICAL') return 'severity-critical'
  if (s === 'HIGH') return 'severity-high'
  if (s === 'MEDIUM') return 'severity-medium'
  return 'severity-low'
})
</script>

<template>
  <div class="priority-badge-container">
    <span v-if="severity" class="severity-badge" :class="severityClass">
      {{ severityLabel }}
    </span>
    <span v-if="priority" class="priority-label">
      ({{ priorityLabel }})
    </span>
  </div>
</template>

<style scoped>
.priority-badge-container {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.severity-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.priority-label {
  color: #a1a1aa;
  font-weight: 500;
}

/* Severity Critical */
.severity-critical {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Severity High */
.severity-high {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

/* Severity Medium */
.severity-medium {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

/* Severity Low */
.severity-low {
  background: rgba(39, 39, 42, 1);
  color: #a1a1aa;
  border: 1px solid rgba(63, 63, 70, 1);
}
</style>
