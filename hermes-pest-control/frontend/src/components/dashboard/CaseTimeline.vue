<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchDecisionRecords,
  fetchToolExecutionRecords,
  fetchHumanReviewItems,
  fetchVisits,
  fetchDocuments,
  isUnauthorizedError,
  type DecisionRecord,
  type ToolExecutionRecord,
  type HumanReviewItem,
  type Visit,
  type OperationalDocument,
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

const decisionRecords = ref<DecisionRecord[]>([])
const toolExecutions = ref<ToolExecutionRecord[]>([])
const humanReviews = ref<HumanReviewItem[]>([])
const visits = ref<Visit[]>([])
const documents = ref<OperationalDocument[]>([])

interface TimelineEvent {
  id: string
  timestamp: string
  dateObj: Date
  type: 'intake' | 'decision' | 'tool' | 'human_review' | 'visit' | 'document'
  title: string
  description: string
  badgeText?: string
  badgeVariant?: 'default' | 'emerald' | 'amber' | 'danger' | 'info' | 'purple'
  icon: string
}

async function loadTimelineData() {
  if (!props.incidentId) return
  loading.value = true
  error.value = null

  try {
    const promises: Promise<any>[] = [
      fetchVisits({ incident_id: props.incidentId }),
      fetchDocuments({ incident_id: props.incidentId }),
    ]

    if (props.conversationId) {
      promises.push(fetchDecisionRecords({ conversation_id: props.conversationId }))
      promises.push(fetchToolExecutionRecords({ limit: 100 }))
      promises.push(fetchHumanReviewItems({ limit: 100 }))
    } else {
      promises.push(Promise.resolve([]))
      promises.push(Promise.resolve([]))
      promises.push(Promise.resolve([]))
    }

    const [loadedVisits, loadedDocs, loadedDecisions, loadedTools, loadedReviews] = await Promise.all(promises)

    visits.value = loadedVisits
    documents.value = loadedDocs
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
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la línea de tiempo'
  } finally {
    loading.value = false
  }
}

const timelineEvents = computed<TimelineEvent[]>(() => {
  const events: TimelineEvent[] = []

  // 1. Intake del Caso (Mensaje Original de Conversación)
  // Generamos un hito inicial basándonos en la fecha de creación del primer decision record o del incidente
  let intakeDate = new Date()
  let channel = 'WEB'
  if (decisionRecords.value.length > 0) {
    const oldest = [...decisionRecords.value].sort(
      (a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime()
    )[0]
    if (oldest.created_at) {
      intakeDate = new Date(oldest.created_at)
      // Restamos 1 minuto para que aparezca primero
      intakeDate.setMinutes(intakeDate.getMinutes() - 1)
    }
    channel = oldest.channel || 'Telegram'
  }

  events.push({
    id: 'intake-start',
    timestamp: intakeDate.toISOString(),
    dateObj: intakeDate,
    type: 'intake',
    title: `Conversación recibida vía ${channel.toUpperCase()}`,
    description: `Mensaje de intake capturado e integrado en el canal de mensajería de Hermes.`,
    badgeText: 'NUEVO MENSAJE',
    badgeVariant: 'purple',
    icon: channel.toLowerCase().includes('whatsapp') ? '💬' : '📱',
  })

  // 2. Decision Records (Clasificación Hermes)
  decisionRecords.value.forEach(dec => {
    if (!dec.created_at) return
    const date = new Date(dec.created_at)
    
    events.push({
      id: `dec-${dec.id}`,
      timestamp: dec.created_at,
      dateObj: date,
      type: 'decision',
      title: dec.incident_should_create ? 'Hermes clasifica la incidencia' : 'Análisis cognitivo del caso',
      description: `Canal: ${dec.channel.toUpperCase()}. Plaga identificada: ${dec.pest_type || 'General'}. Confianza IA: ${(dec as any).confidence || '95%'}.`,
      badgeText: 'IA CLASIFICA',
      badgeVariant: dec.fallback_used ? 'danger' : 'info',
      icon: '🤖',
    })
  })

  // 3. Tool Executions
  toolExecutions.value.forEach(tool => {
    if (!tool.created_at) return
    const date = new Date(tool.created_at)
    const badgeV = tool.review_status === 'approved' ? 'emerald' : tool.review_status === 'rejected' ? 'danger' : 'amber'
    
    events.push({
      id: `tool-${tool.id}`,
      timestamp: tool.created_at,
      dateObj: date,
      type: 'tool',
      title: `Propuesta de herramienta: ${tool.tool_name}`,
      description: `Hermes solicita la ejecución de ${tool.tool_name} (${tool.provider}). Estado de revisión: ${tool.review_status}.`,
      badgeText: `HERRAMIENTA: ${tool.review_status.toUpperCase()}`,
      badgeVariant: badgeV,
      icon: '🔧',
    })
  })

  // 4. Human Reviews (HITL)
  humanReviews.value.forEach(rev => {
    if (!rev.created_at) return
    const date = new Date(rev.created_at)
    events.push({
      id: `rev-created-${rev.id}`,
      timestamp: rev.created_at,
      dateObj: date,
      type: 'human_review',
      title: `Revisión humana requerida`,
      description: `HITL activado. Motivo: ${rev.reason}. Prioridad: ${rev.priority}.`,
      badgeText: 'ESCALADO HITL',
      badgeVariant: 'amber',
      icon: '👤',
    })
    
    if (rev.resolved_at) {
      const resDate = new Date(rev.resolved_at)
      events.push({
        id: `rev-resolved-${rev.id}`,
        timestamp: rev.resolved_at,
        dateObj: resDate,
        type: 'human_review',
        title: `Revisión humana aprobada`,
        description: `Actuación aprobada por el supervisor. Notas: ${rev.resolution_notes || 'Aprobado'}`,
        badgeText: 'HITL RESUELTO',
        badgeVariant: 'emerald',
        icon: '✅',
      })
    }
  })

  // 5. Visits
  visits.value.forEach(v => {
    if (!v.created_at) return
    const dateCreated = new Date(v.created_at)
    events.push({
      id: `visit-created-${v.id}`,
      timestamp: v.created_at,
      dateObj: dateCreated,
      type: 'visit',
      title: 'Visita técnica programada',
      description: `Servicio agendado en dirección: ${v.address || 'S/D'}. Estado: ${v.status}.`,
      badgeText: 'VISITA AGENDADA',
      badgeVariant: 'info',
      icon: '📅',
    })

    if (v.status === 'in_progress' || v.status === 'completed') {
      if (v.updated_at) {
        const dateUpdated = new Date(v.updated_at)
        events.push({
          id: `visit-status-${v.id}-${v.status}`,
          timestamp: v.updated_at,
          dateObj: dateUpdated,
          type: 'visit',
          title: v.status === 'in_progress' ? 'Técnico ha iniciado la visita' : 'Servicio finalizado con éxito',
          description: v.status === 'in_progress' 
            ? `Técnico en camino y ejecución iniciada.` 
            : `Visita finalizada y reporte firmado. Notas del técnico: ${v.notes || 'Control satisfactorio'}.`,
          badgeText: v.status === 'completed' ? 'VISITA COMPLETADA' : 'VISITA EN CURSO',
          badgeVariant: v.status === 'completed' ? 'emerald' : 'amber',
          icon: v.status === 'completed' ? '🏁' : '🚗',
        })
      }
    }
  })

  // 6. Documents (v1, v2, v3)
  documents.value.forEach(doc => {
    if (!doc.created_at) return
    const date = new Date(doc.created_at)
    
    // Si contiene historial en metadata
    const versions = (doc.metadata?.versions as any[]) || []
    if (versions.length > 0) {
      versions.forEach((ver: any) => {
        const verDate = ver.updated_at ? new Date(ver.updated_at) : date
        events.push({
          id: `doc-${doc.id}-v${ver.version}`,
          timestamp: ver.updated_at || doc.created_at || '',
          dateObj: verDate,
          type: 'document',
          title: `Documento generado: ${doc.title} (v${ver.version})`,
          description: `Documento operativo de tipo ${doc.document_type.toUpperCase()} generado por ${doc.generated_by}. Trazabilidad y versión archivada.`,
          badgeText: `DOC V${ver.version}`,
          badgeVariant: 'emerald',
          icon: '📄',
        })
      })
    } else {
      events.push({
        id: `doc-base-${doc.id}`,
        timestamp: doc.created_at,
        dateObj: date,
        type: 'document',
        title: `Documento creado: ${doc.title}`,
        description: `Reporte técnico inicial tipo ${doc.document_type.toUpperCase()}. Autor: ${doc.generated_by}.`,
        badgeText: 'DOC INICIAL',
        badgeVariant: 'default',
        icon: '📄',
      })
    }
  })

  // Ordenar cronológicamente descendente (más recientes arriba)
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

defineExpose({
  refresh: loadTimelineData
})
</script>

<template>
  <div class="case-timeline">
    <div v-if="loading" class="timeline-loading">Cargando cronología del caso...</div>
    <div v-else-if="error" class="timeline-error">{{ error }}</div>
    <div v-else-if="timelineEvents.length === 0" class="timeline-empty">
      No hay eventos registrados para este caso.
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
.case-timeline {
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
  gap: 16px;
  padding-left: 12px;
}

.timeline-flow::before {
  content: '';
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 21px;
  width: 2px;
  background: #27272a;
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
  gap: 4px;
  transition: all 0.2s;
}

.timeline-content:hover {
  border-color: #3f3f46;
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
.badge-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; }

.event-desc {
  font-size: 12px;
  color: #a1a1aa;
  margin: 0;
  line-height: 1.4;
}

.event-time {
  font-size: 10px;
  color: #52525b;
  font-weight: 700;
}
</style>
