<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchConversations,
  fetchConversationMessages,
  sendConversationMessage,
  fetchCustomers,
  type Conversation,
  type Message,
  type Customer
} from '../services/api'
import PageHeader from '../components/dashboard/PageHeader.vue'

const router = useRouter()

const conversations = ref<Conversation[]>([])
const customers = ref<Customer[]>([])
const loading = ref(true)
const selectedConversationId = ref<string | null>(null)
const messages = ref<Message[]>([])
const chatInput = ref('')
const loadingMessages = ref(false)
const sending = ref(false)

// Mapeo rápido de customer_id a Customer
const customersMap = computed(() => {
  const map: Record<string, Customer> = {}
  customers.value.forEach(c => {
    map[c.id] = c
  })
  return map
})

// Cargar Conversaciones y Clientes
async function loadAllConversations() {
  loading.value = true
  try {
    const [convList, custList] = await Promise.all([
      fetchConversations(100),
      fetchCustomers()
    ])
    conversations.value = convList
    customers.value = custList

    if (convList.length > 0) {
      selectedConversationId.value = convList[0].id
    }
  } catch (err) {
    console.error('Error cargando conversaciones:', err)
  } finally {
    loading.value = false
  }
}

// Cargar Mensajes al cambiar de conversación seleccionada
async function loadMessages(convId: string) {
  loadingMessages.value = true
  try {
    const list = await fetchConversationMessages(convId)
    messages.value = list
  } catch (err) {
    console.error('Error al cargar mensajes:', err)
  } finally {
    loadingMessages.value = false
  }
}

// Observar cambio de conversación activa
watch(selectedConversationId, (newId) => {
  if (newId) {
    void loadMessages(newId)
  } else {
    messages.value = []
  }
})

const activeConversation = computed(() => {
  return conversations.value.find(c => c.id === selectedConversationId.value) || null
})

// Enviar Mensaje
async function sendMessage() {
  if (!chatInput.value.trim() || !selectedConversationId.value) return

  sending.value = true
  const msgText = chatInput.value.trim()
  chatInput.value = ''

  try {
    const sentMessage = await sendConversationMessage(selectedConversationId.value, msgText)
    messages.value.push(sentMessage)

    // Auto-scroll del feed al final tras enviar
    setTimeout(() => {
      const el = document.querySelector('.chat-messages-scroll')
      if (el) el.scrollTop = el.scrollHeight
    }, 50)

  } catch (err: any) {
    alert(err?.message || 'Error al enviar el mensaje.')
  } finally {
    sending.value = false
  }
}

function selectConversation(id: string) {
  selectedConversationId.value = id
}

function openCustomerWorkspace() {
  if (activeConversation.value?.customer_id) {
    void router.push(`/customers/${activeConversation.value.customer_id}`)
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

function formatDate(isoString?: string): string {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  void loadAllConversations()
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
          <span class="conversations-count">{{ conversations.length }} Hilos activos</span>
        </header>

        <div class="threads-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="thread-item"
            :class="{ 'active': selectedConversationId === conv.id }"
            @click="selectConversation(conv.id)"
          >
            <div class="thread-header">
              <span class="thread-channel-icon" :class="getChannelStyle(conv.channel).class">
                {{ getChannelStyle(conv.channel).icon }}
              </span>
              <span class="thread-client-name">
                {{ conv.customer_id && customersMap[conv.customer_id] ? customersMap[conv.customer_id].name : 'Contacto ' + getChannelStyle(conv.channel).label }}
              </span>
              <span class="thread-time" v-if="conv.created_at">
                {{ formatDate(conv.created_at) }}
              </span>
            </div>
            <div class="thread-body">
              <span class="thread-pest-type">{{ conv.contact_identifier }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- PANEL DERECHO: Panel de Conversación Activa -->
      <main class="chat-viewport-container" v-if="activeConversation">
        <header class="chat-viewport-header">
          <div class="header-meta">
            <span class="header-icon" :class="getChannelStyle(activeConversation.channel).class">
              {{ getChannelStyle(activeConversation.channel).icon }}
            </span>
            <div>
              <h3>
                {{ activeConversation.customer_id && customersMap[activeConversation.customer_id] ? customersMap[activeConversation.customer_id].name : 'Canal Directo' }}
              </h3>
              <p>Identificador: <b>{{ activeConversation.contact_identifier }}</b> | Canal: <b>{{ getChannelStyle(activeConversation.channel).label }}</b></p>
            </div>
          </div>
          <button
            v-if="activeConversation.customer_id"
            class="primaryButton font-bold text-xs"
            type="button"
            @click="openCustomerWorkspace"
          >
            Ir a Workspace 360°
          </button>
        </header>

        <!-- Mensajes -->
        <div class="chat-messages-scroll">
          <LoadingState v-if="loadingMessages" message="Cargando historial..." />
          <div v-else-if="messages.length === 0" class="no-messages">
            No hay mensajes registrados en esta conversación.
          </div>
          <div
            v-else
            v-for="(msg, idx) in messages"
            :key="msg.id || idx"
            class="bubble-container"
            :class="msg.direction === 'outbound' ? 'sender-supervisor' : 'sender-client'"
          >
            <span class="bubble-avatar">
              {{ msg.direction === 'outbound' ? '👨‍💼' : '👤' }}
            </span>
            <div class="bubble-content">
              <span class="bubble-author">
                {{ msg.direction === 'outbound' ? 'Supervisor (Tú)' : 'Contacto Cliente' }}
              </span>
              <p class="bubble-text">{{ msg.text }}</p>
              <span class="bubble-timestamp">⏱️ {{ formatDate(msg.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Barra inferior de respuesta -->
        <form class="chat-input-bar" @submit.prevent="sendMessage">
          <textarea
            v-model="chatInput"
            placeholder="Escribe una respuesta para el cliente a través del canal operativo..."
            rows="2"
            required
            :disabled="sending"
          ></textarea>
          <button class="primaryButton send-btn" type="submit" :disabled="sending">
            {{ sending ? 'Enviando...' : 'Enviar Mensaje' }}
          </button>
        </form>
      </main>

      <div v-else class="chat-empty-state">
        <div class="empty-icon">✉️</div>
        <h3>No hay conversaciones activas</h3>
        <p>No se encontraron registros de comunicaciones capturadas.</p>
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
  font-family: 'JetBrains Mono', monospace;
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

.no-messages {
  color: #71717a;
  text-align: center;
  font-size: 13px;
  margin: auto;
}

.bubble-container {
  display: flex;
  gap: 12px;
  max-width: 75%;
}

.bubble-container.sender-client {
  align-self: flex-start;
}

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
.sender-supervisor .bubble-content { border-top-right-radius: 0; background: rgba(56, 189, 248, 0.05); border-color: rgba(56, 189, 248, 0.2); }

.bubble-author {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
}

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
