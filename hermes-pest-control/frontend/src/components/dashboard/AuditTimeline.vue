<script setup lang="ts">
import { computed } from 'vue'

export interface AuditEvent {
  id: string
  type: string
  timestamp: string
  description: string
  payload: any
}

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
</script>

<template>
  <div class="audit-timeline">
    <div class="timeline-header">
      <span class="timeline-label">Historial de Operaciones</span>
      <span class="timeline-badge font-mono">Trazabilidad Segura</span>
    </div>
    
    <div class="timeline-body">
      <div v-if="loading && events.length === 0" class="loading-state">
        Cargando historial de auditoría...
      </div>
      <div v-else-if="events.length === 0" class="empty-state">
        No se han registrado eventos de auditoría en este periodo.
      </div>
      <div v-else class="events-list">
        <div v-for="event in events" :key="event.id" class="event-item">
          <div class="event-left">
            <span class="event-icon-box">
              <!-- Default Icon (Gavel / Shield / Gear) -->
              <svg v-if="event.type.includes('POLICY')" class="event-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.746 3.746 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
              </svg>
              <svg v-else-if="event.type.includes('HUMAN')" class="event-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
              <svg v-else class="event-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17L17.25 21A2.67 2.67 0 0021 17.25l-5.83-5.83m-9.75 9.75L9.75 17m-3.03-3.03L3.6 10.85a1 1 0 01-.22-.38l-.9-3.6a1 1 0 011.25-1.22l3.6.9a1 1 0 01.38.22l3.12 3.12m-3.03 3.03l3.03-3.03m3.03 3.03l3.03-3.03M13.5 3h6v6" />
              </svg>
            </span>
            <div class="event-details">
              <div class="event-meta">
                <span class="event-type font-mono">{{ event.type }}</span>
                <span class="event-time font-mono">{{ formatTimestamp(event.timestamp) }}</span>
              </div>
              <p class="event-description">{{ event.description }}</p>
            </div>
          </div>
          <button class="event-btn" @click="emit('inspect-payload', event)">
            <svg class="code-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
            </svg>
            Ver JSON
          </button>
        </div>
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

.events-list {
  display: flex;
  flex-direction: column;
}

.event-item {
  padding: 16px;
  border-bottom: 1px solid #18181b; /* zinc-900 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  transition: background 0.2s;
}

.event-item:hover {
  background: rgba(39, 39, 42, 0.2);
}

.event-item:last-child {
  border-bottom: none;
}

.event-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.event-icon-box {
  background: #09090b;
  border: 1px solid #27272a;
  color: #a1a1aa;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.event-icon {
  width: 18px;
  height: 18px;
}

.event-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.event-type {
  font-size: 11px;
  font-weight: 700;
  color: #f4f4f5;
}

.event-time {
  font-size: 10px;
  color: #71717a;
}

.event-description {
  margin: 0;
  font-size: 12px;
  color: #d4d4d8;
  line-height: 1.4;
  text-align: left;
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
