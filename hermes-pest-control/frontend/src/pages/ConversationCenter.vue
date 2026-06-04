<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchIncidents,
  type Incident
} from '../services/api'
import { formatPestType, formatStatus } from '../utils/labels'
import PageHeader from '../components/dashboard/PageHeader.vue'

const router = useRouter()

const incidents = ref<Incident[]>([])
const loading = ref(true)
const selectedIncidentId = ref<string | null>(null)
const chatInput = ref('')

// Historial local de chat por incidente para interactividad
const chatHistories = ref<Record<string, { sender: 'client' | 'hermes' | 'supervisor', name: string, text: string, time: string }[]>>({})

// Cargar Incidencias
async function loadConversations() {
  try {
    const list = await fetchIncidents({ limit: 50 })
    // Filtrar solo las que tengan canal de intake
    incidents.value = list.filter(i => i.channel)
    
    if (incidents.value.length > 0) {
      selectedIncidentId.value = incidents.value[0].id
    }

    // Inicializar los historiales
    incidents.value.forEach(inc => {
      if (!chatHistories.value[inc.id]) {
        chatHistories.value[inc.id] = generateMockHistory(inc)
      }
    })

  } catch (err) {
    console.error('Error cargando incidencias de chat:', err)
  } finally {
    loading.value = false
  }
}

function generateMockHistory(inc: Incident): { sender: 'client' | 'hermes' | 'supervisor', name: string, text: string, time: string }[] {
  const clientName = inc.location || 'Cliente'
  const pest = formatPestType(inc.pest_type)
  const channel = inc.channel || 'Telegram'
  const dateStr = inc.created_at
    ? new Date(inc.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    : '12:01'

  const channelText = channel.toUpperCase() === 'EMAIL' ? 'correo electrónico' : channel.toUpperCase() === 'WEB' ? 'formulario web' : channel

  return [
    {
      sender: 'client',
      name: 'Contacto Cliente',
      text: `Hola, soy el encargado de ${clientName}. Tenemos presencia de ${pest} en el local (${inc.affected_area || 'cocina y almacén'}). Agradecería que nos programaran una visita técnica urgente.`,
      time: dateStr,
    },
    {
      sender: 'hermes',
      name: 'Hermes IA',
      text: `Hola. He registrado el aviso de intake recibido vía ${channelText} para ${clientName}. Evaluando severidad del vector de plagas...`,
      time: dateStr,
    },
    {
      sender: 'hermes',
      name: 'Hermes IA',
      text: `Incidencia operativa clasificada con prioridad ${inc.priority.toUpperCase()} y SLA de respuesta de ${inc.sla_hours || 4}h. Un supervisor está revisando la planificación de visitas.`,
      time: dateStr,
    }
  ]
}

const activeIncident = computed(() => {
  return incidents.value.find(i => i.id === selectedIncidentId.value) || null
})

const activeChatHistory = computed(() => {
  if (!selectedIncidentId.value) return []
  return chatHistories.value[selectedIncidentId.value] || []
})

// Enviar Mensaje
function sendMessage() {
  if (!chatInput.value.trim() || !selectedIncidentId.value) return
  
  const msgText = chatInput.value.trim()
  chatInput.value = ''
  
  const now = new Date()
  const timeStr = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })

  // 1. Mensaje de Supervisor
  chatHistories.value[selectedIncidentId.value].push({
    sender: 'supervisor',
    name: 'Supervisor (Tú)',
    text: msgText,
    time: timeStr
  })

  // 2. Respuesta automática simulada de Hermes
  setTimeout(() => {
    if (selectedIncidentId.value) {
      chatHistories.value[selectedIncidentId.value].push({
        sender: 'hermes',
        name: 'Hermes IA',
        text: `Entendido. Registrando anotación en la bitácora del incidente: "${msgText}". Mensaje canalizado al técnico asignado.`,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      })
    }
  }, 1000)
}

function selectConversation(id: string) {
  selectedIncidentId.value = id
}

function openWorkspace() {
  if (selectedIncidentId.value) {
    void router.push(`/incidents/${selectedIncidentId.value}`)
  }
}

// Icono y color por canal
function getChannelStyle(channel: string) {
  const c = channel.toLowerCase()
  if (c.includes('tele')) return { icon: '📱', label: 'Telegram', class: 'chan-telegram' }
  if (c.includes('what') || c.includes('wsp')) return { icon: '💬', label: 'WhatsApp', class: 'chan-whatsapp' }
  if (c.includes('email') || c.includes('mail')) return { icon: '✉️', label: 'Email', class: 'chan-email' }
  return { icon: '🌐', label: 'Web', class: 'chan-web' }
}

onMounted(() => {
  void loadConversations()
})
</script>

<template>
  <div class="conversation-center-page">
    <div class="sectionHeader">
      <PageHeader
        title="Centro de Comunicaciones Omnicanal"
        subtitle="Monitoreo y respuesta de conversaciones capturadas en tiempo real por el intake de Hermes (Telegram, WhatsApp, Email, Web)."
      />
    </div>

    <div v-if="loading" class="center-loading">
      Cargando bandeja de entrada omnicanal...
    </div>

    <div v-else class="center-workspace">
      <!-- PANEL IZQUIERDO: Bandeja de Entrada -->
      <aside class="conversations-sidebar">
        <header class="sidebar-header">
          <h3>Bandeja de Entrada</h3>
          <span class="conversations-count">{{ incidents.length }} Hilos activos</span>
        </header>

        <div class="threads-list">
          <div 
            v-for="inc in incidents" 
            :key="inc.id" 
            class="thread-item"
            :class="{ 'active': selectedIncidentId === inc.id }"
            @click="selectConversation(inc.id)"
          >
            <div class="thread-header">
              <span class="thread-channel-icon" :class="getChannelStyle(inc.channel).class">
                {{ getChannelStyle(inc.channel).icon }}
              </span>
              <span class="thread-client-name">{{ inc.location || 'Localización S/D' }}</span>
              <span class="thread-time" v-if="inc.created_at">
                {{ inc.created_at.slice(11, 16) }}
              </span>
            </div>
            <div class="thread-body">
              <span class="thread-pest-type">{{ formatPestType(inc.pest_type) }}</span>
              <p class="thread-snippet" v-if="chatHistories[inc.id]">
                {{ chatHistories[inc.id][chatHistories[inc.id].length - 1].text }}
              </p>
            </div>
          </div>
        </div>
      </aside>

      <!-- PANEL DERECHO: Panel de Conversación Activa -->
      <main class="chat-viewport-container" v-if="activeIncident">
        <header class="chat-viewport-header">
          <div class="header-meta">
            <span class="header-icon" :class="getChannelStyle(activeIncident.channel).class">
              {{ getChannelStyle(activeIncident.channel).icon }}
            </span>
            <div>
              <h3>{{ activeIncident.location || 'Localización S/D' }}</h3>
              <p>Incidencia #{{ activeIncident.id.slice(0, 8).toUpperCase() }} | Prioridad: <b>{{ activeIncident.priority.toUpperCase() }}</b></p>
            </div>
          </div>
          <button class="primaryButton font-bold text-xs" type="button" @click="openWorkspace">
            Ir a Consola 360°
          </button>
        </header>

        <!-- Mensajes -->
        <div class="chat-messages-scroll">
          <div 
            v-for="(msg, idx) in activeChatHistory" 
            :key="idx" 
            class="bubble-container"
            :class="`sender-${msg.sender}`"
          >
            <span class="bubble-avatar">
              {{ msg.sender === 'client' ? '👤' : msg.sender === 'hermes' ? '🤖' : '👨‍💼' }}
            </span>
            <div class="bubble-content">
              <span class="bubble-author">{{ msg.name }}</span>
              <p class="bubble-text">{{ msg.text }}</p>
              <span class="bubble-timestamp">⏱️ {{ msg.time }}</span>
            </div>
          </div>
        </div>

        <!-- Barra inferior de respuesta -->
        <form class="chat-input-bar" @submit.prevent="sendMessage">
          <textarea 
            v-model="chatInput"
            placeholder="Escribe una respuesta para el cliente a través del canal operativo..."
            rows="2"
          ></textarea>
          <button class="primaryButton send-btn" type="submit">Enviar Mensaje</button>
        </form>
      </main>

      <div v-else class="chat-empty-state">
        <div class="empty-icon">✉️</div>
        <h3>No hay conversaciones activas</h3>
        <p>No se encontraron registros de intake de clientes.</p>
      </div>

    </div>
  </div>
</template>

<style scoped>
.conversation-center-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - 120px);
}

.center-loading {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  color: #a1a1aa;
  padding: 80px;
  text-align: center;
  font-weight: 700;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-workspace {
  display: grid;
  grid-template-columns: 320px 1fr;
  border: 1px solid #27272a;
  border-radius: 8px;
  background: #18181b;
  overflow: hidden;
  height: 100%;
}

/* Sidebar Hilos */
.conversations-sidebar {
  border-right: 1px solid #27272a;
  background: #141416;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-header {
  padding: 18px;
  border-bottom: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  font-size: 13px;
  font-weight: 900;
  color: #f4f4f5;
  text-transform: uppercase;
  margin: 0;
}

.conversations-count {
  font-size: 10px;
  color: #71717a;
  font-weight: 700;
}

.threads-list {
  flex-grow: 1;
  overflow-y: auto;
}

.thread-item {
  padding: 14px 18px;
  border-bottom: 1px solid #1f1f23;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.thread-item:hover {
  background: #18181b;
}

.thread-item.active {
  background: #1c1c1f;
  border-left: 3px solid #34d399;
}

.thread-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.thread-channel-icon {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
}

.thread-client-name {
  color: #f4f4f5;
  font-weight: 800;
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thread-time {
  font-size: 10px;
  color: #52525b;
}

.thread-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.thread-pest-type {
  font-size: 10px;
  color: #71717a;
  font-weight: 700;
}

.thread-snippet {
  font-size: 11px;
  color: #a1a1aa;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Chat Viewport */
.chat-viewport-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #09090b;
}

.chat-viewport-header {
  padding: 16px 20px;
  border-bottom: 1px solid #27272a;
  background: #141416;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-meta h3 {
  font-size: 14px;
  font-weight: 850;
  color: #f4f4f5;
  margin: 0;
}

.header-meta p {
  font-size: 11px;
  color: #71717a;
  margin: 2px 0 0 0;
}

.header-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.chat-messages-scroll {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bubble-container {
  display: flex;
  gap: 12px;
  max-width: 75%;
}

.bubble-container.sender-client {
  align-self: flex-start;
}

.bubble-container.sender-hermes,
.bubble-container.sender-supervisor {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.bubble-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1c1c1f;
  border: 1px solid #27272a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.bubble-content {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sender-client .bubble-content { border-top-left-radius: 0; }
.sender-hermes .bubble-content { border-top-right-radius: 0; background: rgba(16, 185, 129, 0.05); border-color: rgba(16, 185, 129, 0.2); }
.sender-supervisor .bubble-content { border-top-right-radius: 0; background: rgba(56, 189, 248, 0.05); border-color: rgba(56, 189, 248, 0.2); }

.bubble-author {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
}

.sender-hermes .bubble-author { color: #34d399; }
.sender-supervisor .bubble-author { color: #38bdf8; }

.bubble-text {
  font-size: 12px;
  color: #e4e4e7;
  margin: 0;
  line-height: 1.4;
}

.bubble-timestamp {
  font-size: 9px;
  color: #52525b;
  align-self: flex-end;
}

.chat-input-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #27272a;
  background: #141416;
  align-items: flex-end;
}

.chat-input-bar textarea {
  flex-grow: 1;
  resize: none;
}

.send-btn {
  height: 42px;
  font-weight: 800;
  white-space: nowrap;
}

/* Colores de Canal */
.chan-telegram { background: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.3); }
.chan-whatsapp { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.chan-email { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.chan-web { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }

.chat-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #71717a;
  height: 100%;
}
.empty-icon { font-size: 48px; }
.chat-empty-state h3 { font-size: 16px; color: #e4e4e7; margin: 0; }
</style>
