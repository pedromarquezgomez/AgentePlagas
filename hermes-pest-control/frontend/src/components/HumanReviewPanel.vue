<script setup lang="ts">
import { ref } from 'vue'
import type { ToolExecution } from '../api/types'
import StatusBadge from './StatusBadge.vue'

defineProps<{
  executions: ToolExecution[]
  loading: boolean
}>()

const emit = defineEmits<{
  approve: [id: string]
  reject: [id: string]
}>()

const processingIds = ref<Record<string, 'approving' | 'rejecting' | null>>({})

async function handleApprove(id: string) {
  processingIds.value[id] = 'approving'
  try {
    await emit('approve', id)
  } finally {
    processingIds.value[id] = null
  }
}

async function handleReject(id: string) {
  processingIds.value[id] = 'rejecting'
  try {
    await emit('reject', id)
  } finally {
    processingIds.value[id] = null
  }
}

function getRiskLabel(risk: number): string {
  if (risk >= 4) return 'CRÍTICO'
  if (risk === 3) return 'ALTO'
  if (risk === 2) return 'MEDIO'
  return 'BAJO'
}

function getRiskColor(risk: number): string {
  if (risk >= 4) return '#ef4444'
  if (risk === 3) return '#f97316'
  if (risk === 2) return '#eab308'
  return '#10b981'
}

function formatToolName(name: string): string {
  if (!name) return 'Herramienta desconocida'
  // Formatear nombres comunes
  if (name.includes('schedule_visit_tool')) return 'Agendar Visita 📅'
  if (name.includes('create_incident_tool')) return 'Crear Incidencia 🪳'
  if (name.includes('send_gmail_draft_tool') || name.includes('gmail')) return 'Borrador Gmail ✉️'
  if (name.includes('telegram')) return 'Telegram 💬'
  if (name.includes('whatsapp')) return 'WhatsApp 🟢'
  return name
}
</script>

<template>
  <div class="human-review-panel" style="background: white; border: 1px solid #d8dee5; border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); padding: 20px; min-height: 300px;">
    <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
      <h3 style="font-size: 16px; font-weight: 800; color: #1e293b; margin: 0;">
        Acciones IA Pendientes de Aprobación
      </h3>
      <span 
        class="badge" 
        style="background: #e0f2fe; color: #0369a1; font-weight: 800; font-size: 12px;"
      >
        {{ executions.length }} propuest{{ executions.length === 1 ? 'a' : 'as' }}
      </span>
    </div>

    <div v-if="loading && executions.length === 0" style="text-align: center; padding: 40px; color: #64748b; font-weight: 600;">
      Cargando propuestas de herramientas...
    </div>

    <div v-else-if="executions.length === 0" style="text-align: center; padding: 45px 20px; color: #64748b; font-size: 14px; display: flex; flex-direction: column; align-items: center; gap: 10px;">
      <div style="font-size: 32px;">✨</div>
      <div style="font-weight: 700; color: #334155;">Cola de revisión limpia</div>
      <div style="color: #64748b; font-size: 12px; max-width: 240px; line-height: 1.4;">
        No hay herramientas de IA en espera de aprobación humana en este momento.
      </div>
    </div>

    <div v-else style="display: flex; flex-direction: column; gap: 16px;">
      <div 
        v-for="item in executions" 
        :key="item.id" 
        style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fafafa; display: flex; flex-direction: column;"
      >
        <!-- Header -->
        <div style="background: #f1f5f9; padding: 12px; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
          <div>
            <div style="font-weight: 800; color: #0f172a; font-size: 13px;">
              {{ formatToolName(item.tool_name) }}
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
              ID: #{{ item.id.slice(0, 8) }} | Canal: {{ item.conversation_id ? 'Chat' : 'Sistema' }}
            </div>
          </div>
          <!-- Badge de Riesgo -->
          <span 
            style="font-size: 10px; font-weight: 900; padding: 3px 8px; border-radius: 4px; color: white;"
            :style="{ background: getRiskColor(item.risk_level) }"
          >
            RIESGO {{ getRiskLabel(item.risk_level) }}
          </span>
        </div>

        <!-- Cuerpo del Payload JSON -->
        <div style="padding: 12px; flex-grow: 1;">
          <div style="font-size: 11px; font-weight: 800; color: #475569; margin-bottom: 6px;">PARÁMETROS PROPUESTOS:</div>
          <pre 
            style="margin: 0; background: #1e293b; color: #f8fafc; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px; overflow-x: auto; max-height: 180px; line-height: 1.4;"
          >{{ JSON.stringify(item.approved_payload || item.metadata || {}, null, 2) }}</pre>
        </div>

        <!-- Botones de Acción -->
        <div style="padding: 10px 12px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 10px;">
          <button 
            class="secondaryButton" 
            style="min-height: 32px; padding: 0 12px; font-size: 12px; font-weight: 700; border-color: #fca5a5; color: #b91c1c; background: #fff5f5; border-radius: 6px;"
            :disabled="processingIds[item.id] !== null && processingIds[item.id] !== undefined"
            @click="handleReject(item.id)"
          >
            {{ processingIds[item.id] === 'rejecting' ? 'Rechazando...' : 'Rechazar' }}
          </button>
          <button 
            class="primaryButton" 
            style="min-height: 32px; padding: 0 12px; font-size: 12px; font-weight: 700; background: #10b981; border-color: #10b981; color: white; border-radius: 6px;"
            :disabled="processingIds[item.id] !== null && processingIds[item.id] !== undefined"
            @click="handleApprove(item.id)"
          >
            {{ processingIds[item.id] === 'approving' ? 'Aprobando...' : 'Aprobar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
button:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-0.5px);
}
</style>
