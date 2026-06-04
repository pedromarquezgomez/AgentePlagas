<script setup lang="ts">
import { computed } from 'vue'
import { formatStatus } from '../../utils/labels'

const props = defineProps<{
  status: string
}>()

const statusLabel = computed(() => formatStatus(props.status))

const colorClass = computed(() => {
  const s = props.status.toLowerCase()
  if (['pending_review', 'new', 'open', 'in_review', 'proposed'].includes(s)) {
    return 'status-warning'
  }
  if (['completed', 'resolved', 'approved', 'executed'].includes(s)) {
    return 'status-success'
  }
  if (['cancelled', 'rejected', 'dismissed', 'blocked'].includes(s)) {
    return 'status-danger'
  }
  if (['waiting_for_client_data', 'needs_more_info', 'draft', 'draft_proposed'].includes(s)) {
    return 'status-info'
  }
  return 'status-default'
})
</script>

<template>
  <span class="status-badge" :class="colorClass">
    <span class="status-dot"></span>
    <span class="status-text">{{ statusLabel }}</span>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: #09090b;
  width: max-content;
  color: #d4d4d8;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Warnings / Pending */
.status-warning .status-dot {
  background: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.status-warning {
  border-color: rgba(245, 158, 11, 0.2);
  color: #fef3c7;
}

/* Success / Completed */
.status-success .status-dot {
  background: #10b981;
}
.status-success {
  border-color: rgba(16, 185, 129, 0.2);
  color: #d1fae5;
}

/* Danger / Cancelled / Blocked */
.status-danger .status-dot {
  background: #ef4444;
}
.status-danger {
  border-color: rgba(239, 68, 68, 0.2);
  color: #fee2e2;
}

/* Info / Drafts / Waiting */
.status-info .status-dot {
  background: #3b82f6;
}
.status-info {
  border-color: rgba(59, 130, 246, 0.2);
  color: #dbeafe;
}

/* Default */
.status-default .status-dot {
  background: #71717a;
}
.status-default {
  border-color: rgba(113, 113, 122, 0.2);
  color: #f4f4f5;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: .5;
  }
}
</style>
