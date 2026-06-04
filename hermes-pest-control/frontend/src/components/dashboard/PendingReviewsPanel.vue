<script setup lang="ts">
import type { ToolExecution } from '../../api/types'
import PriorityBadge from './PriorityBadge.vue'

defineProps<{
  pendingReviews: ToolExecution[]
  loading: boolean
  actionLoadingId: string | null
}>()

const emit = defineEmits<{
  (e: 'approve', id: string): void
  (e: 'reject', id: string): void
  (e: 'inspect', execution: ToolExecution): void
}>()

function formatTimestamp(isoString?: string): string {
  if (!isoString) return '--:--:--'
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch (err) {
    return isoString
  }
}

function getIncidentId(exec: ToolExecution): string {
  const incId = exec.metadata?.incident_id as string | undefined
  if (incId) {
    return `INC-${incId.slice(0, 5).toUpperCase()}`
  }
  return 'GENÉRICO'
}

function getPriority(exec: ToolExecution): string | null {
  return (exec.metadata?.priority as string) || null
}

function getSeverity(exec: ToolExecution): string | null {
  return (exec.metadata?.severity as string) || null
}
</script>

<template>
  <div class="pending-reviews-panel">
    <div class="panel-header">
      <h3 class="panel-title">Cola Human-In-The-Loop (HITL)</h3>
      <span class="panel-badge font-mono">{{ pendingReviews.length }} pendientes</span>
    </div>

    <div class="panel-body">
      <div v-if="loading && pendingReviews.length === 0" class="loading-state">
        Cargando cola de revisión...
      </div>
      <div v-else-if="pendingReviews.length === 0" class="empty-state">
        No hay ejecuciones de herramientas pendientes de autorización humana.
      </div>
      <div v-else class="table-container">
        <table class="reviews-table">
          <thead>
            <tr>
              <th>Herramienta</th>
              <th>Proveedor / Acción</th>
              <th>Incidencia</th>
              <th>Severidad</th>
              <th>Fecha Solicitud</th>
              <th>Estado</th>
              <th class="text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="exec in pendingReviews" :key="exec.id">
              <td class="font-mono text-zinc-100 font-bold">
                {{ exec.tool_name }}
              </td>
              <td>
                <span class="text-zinc-300">{{ exec.provider }}</span>
                <span class="text-zinc-500 font-mono text-xs block">{{ exec.action }}</span>
              </td>
              <td class="font-mono text-zinc-300 font-semibold">
                {{ getIncidentId(exec) }}
              </td>
              <td>
                <PriorityBadge :priority="getPriority(exec)" :severity="getSeverity(exec)" />
              </td>
              <td class="font-mono text-zinc-400 font-medium">
                {{ formatTimestamp(exec.created_at) }}
              </td>
              <td>
                <span class="status-badge proposed">proposed</span>
              </td>
              <td class="text-right">
                <div class="actions-group">
                  <button class="action-btn inspect-btn" @click="emit('inspect', exec)">
                    Ver Payload
                  </button>
                  <button 
                    class="action-btn approve-btn" 
                    :disabled="actionLoadingId !== null"
                    @click="emit('approve', exec.id)"
                  >
                    <span v-if="actionLoadingId === exec.id">Aprobando...</span>
                    <span v-else>Aprobar</span>
                  </button>
                  <button 
                    class="action-btn reject-btn" 
                    :disabled="actionLoadingId !== null"
                    @click="emit('reject', exec.id)"
                  >
                    <span v-if="actionLoadingId === exec.id">Rechazando...</span>
                    <span v-else>Rechazar</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pending-reviews-panel {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #a1a1aa;
  margin: 0;
}

.panel-badge {
  font-size: 10px;
  background: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.panel-body {
  background: #09090b;
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

.reviews-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 12px;
}

.reviews-table th {
  padding: 12px 16px;
  border-bottom: 1px solid #18181b;
  color: #71717a;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.05em;
}

.reviews-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #18181b;
  vertical-align: middle;
}

.reviews-table tr:hover {
  background: rgba(39, 39, 42, 0.2);
}

.text-right {
  text-align: right !important;
}

.text-zinc-100 {
  color: #f4f4f5;
}

.text-zinc-300 {
  color: #d4d4d8;
}

.text-zinc-400 {
  color: #a1a1aa;
}

.text-zinc-500 {
  color: #71717a;
}

.actions-group {
  display: inline-flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  background: #09090b;
  border: 1px solid #27272a;
  color: #a1a1aa;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  border-color: #3f3f46;
  color: #f4f4f5;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.inspect-btn {
  border-color: #27272a;
  color: #a1a1aa;
}

.approve-btn {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
  color: #34d399;
}

.approve-btn:hover:not(:disabled) {
  background: #10b981;
  color: #09090b;
  border-color: #10b981;
}

.reject-btn {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.reject-btn:hover:not(:disabled) {
  background: #ef4444;
  color: #09090b;
  border-color: #ef4444;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.status-badge.proposed {
  background: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
}
</style>
