<script setup lang="ts">
import { computed } from 'vue'
import type { AuditEvent } from '../../api/types'

const props = defineProps<{
  events: AuditEvent[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'inspect-payload', event: AuditEvent): void
}>()

function formatTimestamp(isoString: string): string {
  if (!isoString) return '--:--:--'
  try {
    const date = new Date(isoString)
    return date.toTimeString().split(' ')[0]
  } catch (err) {
    return isoString
  }
}

// Map event types to semantic colors/badges
function getStatusClass(event: AuditEvent): string {
  const type = (event.event_type || '').toLowerCase()
  const status = (event.status || '').toLowerCase()
  const decision = (event.policy_decision || '').toLowerCase()

  if (status === 'approved' || status === 'success' || type === 'tool_execution_completed' || decision === 'allow') {
    return 'badge-green'
  }
  if (status === 'requires_human_review' || status === 'pending' || type === 'human_review_required') {
    return 'badge-yellow'
  }
  if (status === 'rejected' || status === 'cancelled' || type === 'tool_execution_failed') {
    return 'badge-red'
  }
  return 'badge-blue'
}

function getActor(event: AuditEvent): string {
  if (event.user_id) return event.user_id.toUpperCase()
  if (event.channel) return event.channel.toUpperCase()
  return 'SISTEMA'
}

function getIncidentId(event: AuditEvent): string {
  if (event.metadata?.incident_id) {
    return `INC-${event.metadata.incident_id.slice(0, 5).toUpperCase()}`
  }
  if (event.execution_id) {
    return `EXEC-${event.execution_id.slice(0, 5).toUpperCase()}`
  }
  return '--'
}
</script>

<template>
  <div class="audit-timeline">
    <div class="timeline-header">
      <span class="timeline-label">Centro de Gobierno Operativo (Live)</span>
      <span class="timeline-badge font-mono">Trazabilidad Segura</span>
    </div>
    
    <div class="timeline-body">
      <div v-if="loading && events.length === 0" class="loading-state">
        Cargando historial de auditoría...
      </div>
      <div v-else-if="events.length === 0" class="empty-state">
        No se han registrado eventos de auditoría en este periodo.
      </div>
      <div v-else class="table-container">
        <table class="audit-table">
          <thead>
            <tr>
              <th>Hora</th>
              <th>Evento</th>
              <th>Actor</th>
              <th>Incidencia / Ref</th>
              <th>Resultado / Mensaje</th>
              <th class="text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in events" :key="event.event_id">
              <td class="font-mono text-zinc-400 font-medium">
                {{ formatTimestamp(event.timestamp) }}
              </td>
              <td>
                <span class="badge" :class="getStatusClass(event)">
                  {{ event.event_type }}
                </span>
              </td>
              <td class="font-mono text-zinc-300 font-semibold">
                {{ getActor(event) }}
              </td>
              <td class="font-mono text-zinc-300">
                {{ getIncidentId(event) }}
              </td>
              <td class="text-zinc-400 text-left">
                {{ event.message || event.status || '--' }}
              </td>
              <td class="text-right">
                <button class="event-btn" @click="emit('inspect-payload', event)">
                  <svg class="code-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                  </svg>
                  Ver JSON
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.audit-timeline {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  overflow: hidden;
}

.timeline-header {
  padding: 16px;
  border-bottom: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #a1a1aa; /* zinc-400 */
}

.timeline-badge {
  font-size: 10px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399; /* emerald-400 */
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.timeline-body {
  background: #09090b; /* zinc-950 */
}

.loading-state,
.empty-state {
  padding: 40px;
  text-align: center;
  color: #71717a;
  font-size: 12px;
  font-weight: 500;
}

.table-container {
  overflow-x: auto;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 12px;
}

.audit-table th {
  padding: 12px 16px;
  border-bottom: 1px solid #18181b;
  color: #71717a;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
}

.audit-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #18181b;
  vertical-align: middle;
}

.audit-table tr:hover {
  background: rgba(39, 39, 42, 0.2);
}

.text-right {
  text-align: right !important;
}

.text-zinc-300 {
  color: #d4d4d8;
}

.text-zinc-400 {
  color: #a1a1aa;
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.badge-green {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.badge-yellow {
  background: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.badge-red {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.badge-blue {
  background: rgba(14, 165, 233, 0.1);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.2);
}

.event-btn {
  background: #09090b;
  border: 1px solid #27272a;
  color: #a1a1aa;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.event-btn:hover {
  border-color: #3f3f46;
  color: #f4f4f5;
}

.code-icon {
  width: 14px;
  height: 14px;
}
</style>
