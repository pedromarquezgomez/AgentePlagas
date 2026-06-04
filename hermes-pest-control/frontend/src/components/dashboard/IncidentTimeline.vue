<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchDecisionRecords,
  fetchToolExecutionRecords,
  fetchHumanReviewItems,
  fetchVisits,
  isUnauthorizedError,
  type DecisionRecord,
  type ToolExecutionRecord,
  type HumanReviewItem,
  type Visit,
} from '../../services/api'

const props = defineProps<{
  incidentId: string
  conversationId?: string | null
}>()

const emit = defineEmits<{
  unauthorized: []
}>()

const loading = ref(false)
const error = ref<string | null>(null)

// Eventos crudos
const decisionRecords = ref<DecisionRecord[]>([])
const toolExecutions = ref<ToolExecutionRecord[]>([])
const humanReviews = ref<HumanReviewItem[]>([])
const visits = ref<Visit[]>([])

interface TimelineEvent {
  id: string
  timestamp: string
  dateObj: Date
  type: 'decision' | 'tool' | 'human_review' | 'visit'
  title: string
  description: string
  badgeText?: string
  badgeVariant?: 'default' | 'emerald' | 'amber' | 'danger' | 'info'
  icon: string
}

async function loadTimelineData() {
  if (!props.incidentId) return
  loading.value = true
  error.value = null

  try {
    const promises: Promise<any>[] = [
      fetchVisits({ incident_id: props.incidentId }),
    ]

    // Solo consultamos si tenemos conversación
    if (props.conversationId) {
      promises.push(fetchDecisionRecords({ conversation_id: props.conversationId }))
      promises.push(fetchToolExecutionRecords({ limit: 100 })) // Filtramos en cliente por conversation_id
      promises.push(fetchHumanReviewItems({ limit: 100 })) // Filtramos en cliente por incident_id o conversation_id
    } else {
      promises.push(Promise.resolve([]))
      promises.push(Promise.resolve([]))
      promises.push(Promise.resolve([]))
    }

    const [loadedVisits, loadedDecisions, loadedTools, loadedReviews] = await Promise.all(promises)

    visits.value = loadedVisits
    decisionRecords.value = loadedDecisions

    if (props.conversationId) {
      toolExecutions.value = (loadedTools as ToolExecutionRecord[]).filter(
        t => t.conversation_id === props.conversationId
      )
      humanReviews.value = (loadedReviews as HumanReviewItem[]).filter(
        r => r.incident_id === props.incidentId || r.conversation_id === props.conversationId
      )
    } else {
      toolExecutions.value = []
      humanReviews.value = []
    }
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar el timeline'
  } finally {
    loading.value = false
  }
}

// Mapeador unificado de eventos
const timelineEvents = computed<TimelineEvent[]>(() => {
  const events: TimelineEvent[] = []

  // 1. Decision Records
  decisionRecords.value.forEach(dec => {
    const date = dec.created_at ? new Date(dec.created_at) : new Date()
    let desc = `Acción propuesta: ${dec.action_type || 'Ninguna'}`
    if (dec.fallback_used) {
      desc += ` (Usó fallback: ${dec.fallback_reason || 'Riesgo / Error'})`
    }
    
    events.push({
      id: `dec-${dec.id}`,
      timestamp: dec.created_at || '',
      dateObj: date,
      type: 'decision',
      title: dec.incident_should_create ? 'Hermes clasifica la incidencia' : 'Mensaje analizado por la IA',
      description: desc,
      badgeText: dec.hermes_mode === 'mock' ? 'MOCK' : 'IA REAL',
      badgeVariant: dec.fallback_used ? 'danger' : 'info',
      icon: '🤖',
    })
  })

  // 2. Tool Executions
  toolExecutions.value.forEach(tool => {
    const date = tool.created_at ? new Date(tool.created_at) : new Date()
    const badgeV = tool.review_status === 'approved' ? 'emerald' : tool.review_status === 'rejected' ? 'danger' : 'amber'
    events.push({
      id: `tool-${tool.id}`,
      timestamp: tool.created_at || '',
      dateObj: date,
      type: 'tool',
      title: `Herramienta propuesta: ${tool.tool_name}`,
      description: `Proveedor: ${tool.provider || 'S/D'}. Estado de revisión: ${tool.review_status}. Ejecutado: ${tool.executed ? 'Sí' : 'No'}`,
      badgeText: tool.review_status.toUpperCase(),
      badgeVariant: badgeV,
      icon: '🔧',
    })
  })

  // 3. Human Reviews
  humanReviews.value.forEach(rev => {
    const date = rev.created_at ? new Date(rev.created_at) : new Date()
    events.push({
      id: `rev-created-${rev.id}`,
      timestamp: rev.created_at || '',
      dateObj: date,
      type: 'human_review',
      title: `Revision Humana: ${rev.reason}`,
      description: `Prioridad: ${rev.priority}. Estado: ${rev.status}`,
      badgeText: `HITL: ${rev.status.toUpperCase()}`,
      badgeVariant: rev.status === 'resolved' ? 'emerald' : 'amber',
      icon: '👤',
    })
    
    if (rev.resolved_at) {
      const resDate = new Date(rev.resolved_at)
      events.push({
        id: `rev-resolved-${rev.id}`,
        timestamp: rev.resolved_at,
        dateObj: resDate,
        type: 'human_review',
        title: `Revisión Humana Resuelta`,
        description: `Notas de resolución: ${rev.resolution_notes || 'Sin notas'}. Asignado a: ${rev.assigned_to || 'Nadie'}`,
        badgeText: 'RESUELTO',
        badgeVariant: 'emerald',
        icon: '✅',
      })
    }
  })

  // 4. Visits
  visits.value.forEach(v => {
    // Evento de creación de visita
    const dateCreated = v.created_at ? new Date(v.created_at) : new Date()
    events.push({
      id: `visit-created-${v.id}`,
      timestamp: v.created_at || '',
      dateObj: dateCreated,
      type: 'visit',
      title: 'Visita técnica planificada',
      description: `Dirección: ${v.address || 'S/D'}. Estado: ${v.status}`,
      badgeText: 'PLANIFICADA',
      badgeVariant: 'info',
      icon: '📅',
    })

    // Si está en curso o completada, simulamos sus hitos para enriquecer el timeline
    if (v.status === 'in_progress' || v.status === 'completed') {
      const dateUpdated = v.updated_at ? new Date(v.updated_at) : new Date()
      // Generamos un hito de estado en el timeline
      events.push({
        id: `visit-status-${v.id}-${v.status}`,
        timestamp: v.updated_at || '',
        dateObj: dateUpdated,
        type: 'visit',
        title: v.status === 'in_progress' ? 'Técnico ha iniciado la visita' : 'Visita finalizada',
        description: `El técnico cambió el estado de la visita a: ${v.status}. Notas: ${v.notes || 'Sin notas'}`,
        badgeText: v.status.toUpperCase(),
        badgeVariant: v.status === 'completed' ? 'emerald' : 'amber',
        icon: v.status === 'completed' ? '🏁' : '🚗',
      })
    }
  })

  // Ordenar cronológicamente ascendente (del más antiguo al más reciente) o descendente
  // Vamos a usar descendente (más recientes primero)
  return events.sort((a, b) => b.dateObj.getTime() - a.dateObj.getTime())
})

function formatDate(value: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

watch(
  () => props.incidentId,
  () => {
    void loadTimelineData()
  },
  { immediate: true }
)
</script>

<template>
  <div class="timeline-widget">
    <div v-if="loading" class="timeline-loading">Cargando cronología...</div>
    <div v-else-if="error" class="timeline-error">{{ error }}</div>
    <div v-else-if="timelineEvents.length === 0" class="timeline-empty">
      No hay eventos registrados en la cronología de este caso.
    </div>

    <div v-else class="timeline-flow">
      <div 
        v-for="event in timelineEvents" 
        :key="event.id" 
        class="timeline-item"
        :class="`type-${event.type}`"
      >
        <div class="timeline-marker">
          <span class="marker-icon">{{ event.icon }}</span>
        </div>
        
        <div class="timeline-content">
          <div class="content-header">
            <span class="event-title">{{ event.title }}</span>
            <span v-if="event.badgeText" class="event-badge" :class="`badge-${event.badgeVariant}`">
              {{ event.badgeText }}
            </span>
          </div>
          
          <p class="event-desc">{{ event.description }}</p>
          <time class="event-time">⏱️ {{ formatDate(event.timestamp) }}</time>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-widget {
  width: 100%;
}

.timeline-loading,
.timeline-empty {
  padding: 16px;
  color: #71717a;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}

.timeline-error {
  padding: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
}

.timeline-flow {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-left: 12px;
}

/* Línea de unión vertical */
.timeline-flow::before {
  content: '';
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 21px;
  width: 2px;
  background: #27272a; /* zinc-800 */
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.timeline-marker {
  position: relative;
  z-index: 10;
  width: 20px;
  height: 20px;
  background: #18181b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-icon {
  font-size: 12px;
  user-select: none;
}

.timeline-content {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 12px 16px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.event-title {
  font-size: 13px;
  font-weight: 800;
  color: #f4f4f5;
}

.event-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.badge-default { background: #27272a; color: #a1a1aa; }
.badge-info { background: rgba(14, 165, 233, 0.15); color: #38bdf8; }
.badge-emerald { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.event-desc {
  font-size: 12px;
  color: #a1a1aa;
  margin: 0;
  line-height: 1.4;
}

.event-time {
  font-size: 10px;
  color: #71717a;
  font-weight: 600;
}
</style>
