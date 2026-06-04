<script setup lang="ts">
import { ref } from 'vue'
import type { Incident } from '../api/types'
import StatusBadge from './StatusBadge.vue'
import SlaBadge from './SlaBadge.vue'

const props = defineProps<{
  incidents: Incident[]
  loading: boolean
}>()

const emit = defineEmits<{
  'update-incident': [id: string, payload: Partial<Incident>]
}>()

const editingIncidentId = ref<string | null>(null)
const editStatus = ref('')
const editPriority = ref('')
const editNotes = ref('')
const savingId = ref<string | null>(null)

const statusOptions = [
  { value: 'pending_review', label: 'Pendiente revisión' },
  { value: 'waiting_for_client_data', label: 'Esperando datos' },
  { value: 'ready_for_scheduling', label: 'Listo para agendar' },
  { value: 'scheduled', label: 'Agendado' },
  { value: 'in_progress', label: 'En curso' },
  { value: 'completed', label: 'Completado' },
  { value: 'closed', label: 'Cerrado' },
  { value: 'cancelled', label: 'Cancelado' },
]

const priorityOptions = [
  { value: 'low', label: 'Baja' },
  { value: 'medium', label: 'Media' },
  { value: 'high', label: 'Alta' },
  { value: 'urgent', label: 'Urgente' },
]

function startEditing(incident: Incident) {
  editingIncidentId.value = incident.id
  editStatus.value = incident.status
  editPriority.value = incident.priority
  editNotes.value = incident.internal_notes || ''
}

function cancelEditing() {
  editingIncidentId.value = null
}

async function saveChanges(incidentId: string) {
  savingId.value = incidentId
  try {
    await emit('update-incident', incidentId, {
      status: editStatus.value,
      priority: editPriority.value,
      internal_notes: editNotes.value || null,
    })
    editingIncidentId.value = null
  } finally {
    savingId.value = null
  }
}

function formatPest(pest: string | null | undefined): string {
  if (!pest) return 'N/A'
  switch (pest.toUpperCase()) {
    case 'COCKROACH': return 'Cucarachas 🪳'
    case 'RODENT': return 'Roedores 🐀'
    case 'ANT': return 'Hormigas 🐜'
    case 'FLYING_INSECT': return 'Insectos Voladores 🪰'
    case 'STORED_PRODUCT_INSECT': return 'Plagas de Almacén 🐛'
    default: return pest
  }
}

function formatChannel(channel: string): string {
  if (!channel) return 'N/A'
  const c = channel.toLowerCase()
  if (c === 'telegram') return 'Telegram 💬'
  if (c === 'whatsapp') return 'WhatsApp 🟢'
  return channel
}
</script>

<template>
  <div class="tableShell" style="border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); overflow: hidden;">
    <table class="incidentTable" style="width: 100%; border-collapse: collapse; min-width: 1000px;">
      <thead>
        <tr style="background: #f8fafc;">
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 140px;">ID / FECHA</th>
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 130px;">CANAL</th>
          <th style="padding: 16px; font-weight: 800; color: #475569;">PLAGA / UBICACIÓN</th>
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 120px;">PRIORIDAD</th>
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 160px;">ESTADO</th>
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 140px;">SLA</th>
          <th style="padding: 16px; font-weight: 800; color: #475569; width: 160px; text-align: right;">ACCIONES</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading && incidents.length === 0">
          <td colspan="7" style="text-align: center; padding: 40px; color: #64748b; font-weight: 600;">
            Cargando incidencias operativas...
          </td>
        </tr>
        <tr v-else-if="incidents.length === 0">
          <td colspan="7" style="text-align: center; padding: 40px; color: #64748b; font-weight: 600;">
            No se encontraron incidencias activas en el sistema.
          </td>
        </tr>
        <template v-else v-for="incident in incidents" :key="incident.id">
          <!-- Fila Normal -->
          <tr 
            style="border-bottom: 1px solid #f1f5f9; transition: background 0.2s;"
            :style="{ background: editingIncidentId === incident.id ? '#f8fafc' : '#ffffff' }"
          >
            <td style="padding: 16px; vertical-align: middle;">
              <div style="font-weight: 800; color: #0f172a; font-size: 13px;">#{{ incident.id.slice(0, 8) }}</div>
              <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                {{ incident.created_at ? new Date(incident.created_at).toLocaleDateString('es-ES') : 'N/A' }}
              </div>
            </td>
            <td style="padding: 16px; vertical-align: middle;">
              <span style="font-weight: 700; color: #475569; font-size: 13px;">
                {{ formatChannel(incident.channel) }}
              </span>
            </td>
            <td style="padding: 16px; vertical-align: middle;">
              <div style="font-weight: 800; color: #1e293b;">
                {{ formatPest(incident.pest_type) }}
              </div>
              <div style="font-size: 12px; color: #64748b; margin-top: 3px; display: flex; flex-direction: column;">
                <span><strong>Dirección:</strong> {{ incident.location || 'No especificada' }}</span>
                <span v-if="incident.affected_area"><strong>Área:</strong> {{ incident.affected_area }}</span>
              </div>
            </td>
            <td style="padding: 16px; vertical-align: middle;">
              <!-- Prioridad de visualización -->
              <span 
                class="badge" 
                :class="{
                  'priority-urgent': incident.priority === 'urgent',
                  'priority-high': incident.priority === 'high',
                  'priority-medium': incident.priority === 'medium',
                  'priority-low': incident.priority === 'low'
                }"
                style="text-transform: uppercase; font-size: 11px; letter-spacing: 0.03em;"
              >
                {{ incident.priority }}
              </span>
            </td>
            <td style="padding: 16px; vertical-align: middle;">
              <StatusBadge :status="incident.status" type="incident" />
            </td>
            <td style="padding: 16px; vertical-align: middle;">
              <SlaBadge :status="incident.sla_status" />
              <div v-if="incident.remaining_hours !== undefined && incident.remaining_hours !== null" style="font-size: 11px; color: #64748b; margin-top: 4px;">
                <span v-if="incident.remaining_hours > 0">Restan {{ incident.remaining_hours.toFixed(1) }}h</span>
                <span v-else style="color: #ef4444; font-weight: 700;">Vencido por {{ Math.abs(incident.remaining_hours).toFixed(1) }}h</span>
              </div>
            </td>
            <td style="padding: 16px; vertical-align: middle; text-align: right;">
              <button 
                v-if="editingIncidentId !== incident.id"
                class="secondaryButton" 
                style="padding: 6px 12px; font-size: 13px; font-weight: 700; border-radius: 6px; cursor: pointer; transition: all 0.2s;"
                @click="startEditing(incident)"
              >
                Editar
              </button>
              <span v-else style="color: #64748b; font-size: 13px; font-weight: 600;">Editando...</span>
            </td>
          </tr>

          <!-- Fila de Edición Expandida -->
          <tr v-if="editingIncidentId === incident.id" style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
            <td colspan="7" style="padding: 20px; border-top: 1px dashed #cbd5e1;">
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; align-items: start;">
                <!-- Estado -->
                <div>
                  <label style="font-size: 12px; font-weight: 800; color: #475569; margin-bottom: 8px; display: block;">
                    ESTADO INCIDENCIA
                  </label>
                  <select v-model="editStatus" style="width: 100%; min-width: 0; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: white;">
                    <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>

                <!-- Prioridad -->
                <div>
                  <label style="font-size: 12px; font-weight: 800; color: #475569; margin-bottom: 8px; display: block;">
                    PRIORIDAD OPERATIVA
                  </label>
                  <select v-model="editPriority" style="width: 100%; min-width: 0; height: 38px; border-radius: 6px; border: 1px solid #cbd5e1; background: white;">
                    <option v-for="opt in priorityOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                </div>

                <!-- Notas Internas -->
                <div style="grid-column: span 2;">
                  <label style="font-size: 12px; font-weight: 800; color: #475569; margin-bottom: 8px; display: block;">
                    NOTAS INTERNAS / OBSERVACIONES
                  </label>
                  <textarea 
                    v-model="editNotes" 
                    placeholder="Escribe comentarios internos sobre el incidente o estado de resolución..."
                    style="width: 100%; min-height: 80px; padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 13px; background: white; resize: vertical;"
                  ></textarea>
                </div>
              </div>

              <!-- Botones de Acción de Edición -->
              <div style="margin-top: 16px; display: flex; justify-content: flex-end; gap: 12px;">
                <button 
                  class="secondaryButton" 
                  style="padding: 8px 16px; font-size: 13px; border-radius: 6px;"
                  :disabled="savingId === incident.id"
                  @click="cancelEditing"
                >
                  Cancelar
                </button>
                <button 
                  class="primaryButton" 
                  style="padding: 8px 16px; font-size: 13px; border-radius: 6px; display: flex; align-items: center; gap: 6px;"
                  :disabled="savingId === incident.id"
                  @click="saveChanges(incident.id)"
                >
                  <span v-if="savingId === incident.id">Guardando...</span>
                  <span v-else>Guardar Cambios</span>
                </button>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
