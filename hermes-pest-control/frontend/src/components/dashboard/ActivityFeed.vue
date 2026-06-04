<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDecisionRecords,
  fetchToolExecutionRecords,
  fetchVisits,
  fetchTechnicians,
  type Visit,
  type DecisionRecord,
  type ToolExecutionRecord,
  type Technician,
} from '../../services/api'

const loading = ref(false)
const error = ref<string | null>(null)

const visits = ref<Visit[]>([])
const decisionRecords = ref<DecisionRecord[]>([])
const toolExecutions = ref<ToolExecutionRecord[]>([])
const technicians = ref<Technician[]>([])

interface ActivityItem {
  id: string
  text: string
  timeStr: string
  dateObj: Date
  icon: string
  variant: 'info' | 'success' | 'warning' | 'danger'
}

async function loadFeed() {
  loading.value = true
  error.value = null
  try {
    const [loadedVisits, loadedDecisions, loadedTools, loadedTechs] = await Promise.all([
      fetchVisits({ limit: 50 }),
      fetchDecisionRecords({ limit: 50 }),
      fetchToolExecutionRecords({ limit: 50 }),
      fetchTechnicians({ limit: 200 }),
    ])
    
    visits.value = loadedVisits
    decisionRecords.value = loadedDecisions
    toolExecutions.value = loadedTools
    technicians.value = loadedTechs
  } catch (err) {
    console.error('Error cargando feed de actividad:', err)
    error.value = 'No se pudo cargar el feed de actividad operativa'
  } finally {
    loading.value = false
  }
}

function getTechnicianName(techId: string | null | undefined): string {
  if (!techId) return 'Técnico'
  return technicians.value.find(t => t.id === techId)?.name || 'Técnico'
}

const feedItems = computed<ActivityItem[]>(() => {
  const items: ActivityItem[] = []

  // Mapeamos visitas
  visits.value.forEach(v => {
    if (!v.updated_at) return
    const date = new Date(v.updated_at)
    
    let text = ''
    let icon = '📅'
    let variant: 'info' | 'success' | 'warning' | 'danger' = 'info'

    if (v.status === 'scheduled') {
      text = `Visita programada para la incidencia #${v.incident_id.slice(0, 6)} asignada a ${getTechnicianName(v.technician_id)}`
      icon = '📅'
      variant = 'info'
    } else if (v.status === 'in_progress') {
      text = `El técnico ${getTechnicianName(v.technician_id)} ha iniciado la visita para la incidencia #${v.incident_id.slice(0, 6)}`
      icon = '🚗'
      variant = 'warning'
    } else if (v.status === 'completed') {
      text = `El técnico ${getTechnicianName(v.technician_id)} completó con éxito la visita de control de plagas`
      icon = '🏁'
      variant = 'success'
    } else if (v.status === 'cancelled') {
      text = `Se canceló la visita asignada a ${getTechnicianName(v.technician_id)}`
      icon = '❌'
      variant = 'danger'
    } else {
      return
    }

    items.push({
      id: `visit-${v.id}-${v.status}-${v.updated_at}`,
      text,
      timeStr: v.updated_at,
      dateObj: date,
      icon,
      variant,
    })
  })

  // Mapeamos Decision Records
  decisionRecords.value.forEach(dec => {
    if (!dec.created_at) return
    const date = new Date(dec.created_at)
    
    let text = ''
    let icon = '🤖'
    let variant: 'info' | 'success' | 'warning' | 'danger' = 'info'

    if (dec.incident_should_create) {
      text = `Nueva incidencia creada automáticamente por Hermes (${dec.pest_type || 'Plaga general'})`
      icon = '🪳'
      variant = 'success'
    } else if (dec.action_type === 'escalate_to_human') {
      text = `Hermes escaló un caso a revisión humana debido a complejidad o prioridad alta`
      icon = '👤'
      variant = 'warning'
    } else {
      text = `Hermes procesó un mensaje del canal ${dec.channel.toUpperCase()}`
      icon = '🤖'
      variant = 'info'
    }

    items.push({
      id: `dec-${dec.id}`,
      text,
      timeStr: dec.created_at,
      dateObj: date,
      icon,
      variant,
    })
  })

  // Mapeamos Tool Executions
  toolExecutions.value.forEach(tool => {
    if (!tool.created_at) return
    const date = new Date(tool.created_at)
    
    let text = ''
    let icon = '🔧'
    let variant: 'info' | 'success' | 'warning' | 'danger' = 'info'

    if (tool.review_status === 'proposed') {
      text = `Hermes propuso la ejecución de herramienta: ${tool.tool_name}`
      icon = '💡'
      variant = 'warning'
    } else if (tool.review_status === 'approved') {
      text = `Supervisor aprobó la actuación de herramienta: ${tool.tool_name}`
      icon = '✅'
      variant = 'success'
    } else if (tool.review_status === 'rejected') {
      text = `Supervisor rechazó la propuesta de herramienta: ${tool.tool_name}`
      icon = '🚫'
      variant = 'danger'
    } else {
      return
    }

    items.push({
      id: `tool-${tool.id}-${tool.review_status}`,
      text,
      timeStr: tool.created_at,
      dateObj: date,
      icon,
      variant,
    })
  })

  // Ordenar y limitar a las 10 más recientes
  return items
    .sort((a, b) => b.dateObj.getTime() - a.dateObj.getTime())
    .slice(0, 10)
})

function formatTime(value: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  
  // Mostrar de forma relativa o hora del día
  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

onMounted(() => {
  void loadFeed()
})

defineExpose({
  refresh: loadFeed
})
</script>

<template>
  <div class="activity-feed-card">
    <div class="feed-header">
      <div class="header-left">
        <h3 class="feed-title">Actividad Reciente</h3>
        <p class="feed-subtitle">Hitos operativos en tiempo real en la plataforma</p>
      </div>
      <button class="secondaryButton refresh-feed-btn" type="button" :disabled="loading" @click="loadFeed">
        🔄
      </button>
    </div>

    <div v-if="loading" class="feed-loading">Cargando actividad...</div>
    <div v-else-if="error" class="feed-error">{{ error }}</div>
    <div v-else-if="feedItems.length === 0" class="feed-empty">
      No hay actividad reciente registrada en las últimas horas.
    </div>

    <div v-else class="feed-list">
      <div 
        v-for="item in feedItems" 
        :key="item.id" 
        class="feed-item"
        :class="`variant-${item.variant}`"
      >
        <span class="feed-icon">{{ item.icon }}</span>
        <div class="feed-content">
          <p class="feed-text">{{ item.text }}</p>
          <time class="feed-time">⏱️ {{ formatTime(item.timeStr) }}</time>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.activity-feed-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-title {
  font-size: 15px;
  font-weight: 800;
  color: #e4e4e7;
  margin: 0;
}

.feed-subtitle {
  color: #71717a;
  font-size: 11px;
  margin: 0;
  font-weight: 600;
}

.refresh-feed-btn {
  min-height: 32px;
  min-width: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.feed-loading,
.feed-empty {
  padding: 24px;
  color: #71717a;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.feed-error {
  padding: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}

.feed-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 10px;
  background: #09090b;
  border-radius: 6px;
  border: 1px solid #1f1f23;
  transition: background 0.2s;
}

.feed-item:hover {
  background: #121214;
}

.feed-icon {
  font-size: 16px;
  background: #18181b;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feed-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-grow: 1;
}

.feed-text {
  font-size: 12px;
  color: #d4d4d8;
  margin: 0;
  line-height: 1.4;
  font-weight: 650;
}

.feed-time {
  font-size: 10px;
  color: #52525b;
  font-weight: 700;
}

/* Bordes sutiles según la variante */
.feed-item.variant-info { border-left: 2px solid #38bdf8; }
.feed-item.variant-success { border-left: 2px solid #10b981; }
.feed-item.variant-warning { border-left: 2px solid #f59e0b; }
.feed-item.variant-danger { border-left: 2px solid #ef4444; }
</style>
