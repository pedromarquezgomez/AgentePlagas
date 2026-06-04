<script setup lang="ts">
import { ref } from 'vue'
import type { Incident } from '../../api/types'
import StatusBadge from './StatusBadge.vue'
import SlaBadge from './SlaBadge.vue'
import PriorityBadge from './PriorityBadge.vue'
import { formatPestType, formatChannel, formatVisitType } from '../../utils/labels'

const props = defineProps<{
  incidents: Incident[]
  loading: boolean
  actionLoadingId?: string | null
}>()

const emit = defineEmits<{
  (e: 'approve', incidentId: string): void
  (e: 'cancel', incidentId: string): void
  (e: 'inspect', incident: Incident): void
}>()
</script>

<template>
  <div class="table-container">
    <div class="table-header">
      <div>
        <h3 class="table-title">Cola Principal de Decisiones</h3>
        <p class="table-subtitle">Todos los datos de SLA, severidad e incidencias se resuelven de forma estricta en el servidor backend.</p>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="dense-table">
        <thead>
          <tr>
            <th>ID de Incidencia / Ubicación</th>
            <th>Plaga Detectada / Canal</th>
            <th>Prioridad / Severidad</th>
            <th>Asignación Técnica</th>
            <th>Estado SLA (Backend)</th>
            <th>Estado del Proceso</th>
            <th class="text-right">Acciones (HITL)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && incidents.length === 0">
            <td colspan="7" class="state-cell">
              <div class="loading-spinner">Cargando incidencias operativas...</div>
            </td>
          </tr>
          <tr v-else-if="incidents.length === 0" class="empty-row">
            <td colspan="7" class="state-cell">
              Ninguna incidencia activa coincide con los criterios de filtrado.
            </td>
          </tr>
          <tr v-for="incident in incidents" :key="incident.id" class="data-row">
            <!-- ID / Ubicación -->
            <td>
              <div class="id-cell">
                <span class="incident-hash font-mono">#{{ incident.id.slice(0, 8).toUpperCase() }}</span>
              </div>
              <div class="location-text">
                <svg class="loc-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25s-7.5-4.108-7.5-11.25a3 3 0 0119.5 10.5z" />
                </svg>
                {{ incident.location || 'Calle Larios, Málaga' }}
              </div>
            </td>

            <!-- Plaga / Canal -->
            <td>
              <div class="pest-container">
                <span class="pest-badge font-mono">{{ formatPestType(incident.pest_type) }}</span>
                <span class="channel-text">{{ formatChannel(incident.channel) }}</span>
              </div>
            </td>

            <!-- Prioridad / Severidad -->
            <td>
              <PriorityBadge 
                :priority="incident.operational_priority || incident.priority" 
                :severity="incident.severity"
              />
            </td>

            <!-- Nivel Técnico / Visit Type -->
            <td>
              <div class="technical-assign font-mono">
                <span class="level-tag">Nivel {{ incident.technician_level || 'STANDARD' }}</span>
                <span class="visit-type-text">{{ incident.visit_type ? formatVisitType(incident.visit_type) : 'Inspección' }}</span>
              </div>
            </td>

            <!-- Estado SLA -->
            <td>
              <SlaBadge 
                :slaStatus="incident.sla_status || 'ON_TRACK'" 
                :remainingHours="incident.remaining_hours"
                :breachHours="incident.breach_hours"
              />
            </td>

            <!-- Estado del Proceso -->
            <td>
              <StatusBadge :status="incident.status" />
            </td>

            <!-- Acciones -->
            <td class="text-right">
              <div class="actions-cell">
                <button 
                  @click="emit('inspect', incident)"
                  class="action-btn btn-inspect"
                  title="Inspeccionar JSON"
                >
                  <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                  </svg>
                </button>

                <button 
                  v-if="incident.status === 'pending_review' || incident.status === 'new'"
                  @click="emit('approve', incident.id)" 
                  :disabled="actionLoadingId === incident.id"
                  class="action-btn btn-confirm"
                >
                  Confirmar
                </button>

                <button 
                  v-if="incident.status !== 'cancelled' && incident.status !== 'closed' && incident.status !== 'completed'"
                  @click="emit('cancel', incident.id)" 
                  :disabled="actionLoadingId === incident.id"
                  class="action-btn btn-cancel"
                >
                  Cancelar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.table-container {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  margin-top: 24px;
}

.table-header {
  padding: 16px 20px;
  border-bottom: 1px solid #27272a;
}

.table-title {
  font-size: 14px;
  font-weight: 700;
  color: #f4f4f5;
  margin: 0;
}

.table-subtitle {
  font-size: 11px;
  color: #71717a;
  margin: 4px 0 0 0;
}

.table-wrapper {
  overflow-x: auto;
}

.dense-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 12px;
}

.dense-table th {
  background: #09090b; /* zinc-950 */
  color: #a1a1aa; /* zinc-400 */
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 12px 16px;
  border-bottom: 1px solid #27272a;
}

.dense-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #18181b; /* zinc-900 */
  vertical-align: middle;
  color: #d4d4d8;
}

.data-row:hover {
  background: rgba(39, 39, 42, 0.4); /* zinc-800 / 40 */
}

.id-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.incident-hash {
  font-weight: 700;
  color: #f4f4f5;
  font-size: 13px;
}

.location-text {
  font-size: 11px;
  color: #71717a;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.loc-icon {
  width: 12px;
  height: 12px;
  color: #52525b;
}

.pest-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.pest-badge {
  background: #09090b;
  border: 1px solid #27272a;
  color: #e4e4e7;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.channel-text {
  font-size: 10px;
  color: #71717a;
  text-transform: uppercase;
  font-weight: 600;
}

.technical-assign {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.level-tag {
  background: #09090b;
  border: 1px solid #27272a;
  color: #d4d4d8;
  padding: 2px 6px;
  border-radius: 4px;
  width: max-content;
  font-size: 10px;
}

.visit-type-text {
  font-size: 10px;
  color: #71717a;
  text-transform: uppercase;
  font-weight: 600;
}

.actions-cell {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.text-right {
  text-align: right;
}

.action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn-inspect {
  background: #09090b;
  border-color: #27272a;
  color: #71717a;
  padding: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-inspect:hover {
  border-color: #3f3f46;
  color: #f4f4f5;
}

.action-icon {
  width: 14px;
  height: 14px;
}

.btn-confirm {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.25);
  color: #34d399; /* emerald-400 */
}

.btn-confirm:hover {
  background: #059669; /* emerald-600 */
  color: #ffffff;
  border-color: transparent;
}

.btn-cancel {
  background: #27272a;
  border-color: #3f3f46;
  color: #d4d4d8;
}

.btn-cancel:hover {
  background: #3f3f46;
  color: #f4f4f5;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.state-cell {
  padding: 40px;
  text-align: center;
  color: #71717a;
  font-weight: 600;
}

.empty-row {
  background: transparent;
}

.loading-spinner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
