<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import {
  fetchCustomer,
  updateCustomer,
  fetchCustomerSites,
  createCustomerSite,
  fetchCustomerContracts,
  createCustomerContract,
  fetchIncidents,
  fetchVisits,
  fetchConversations,
  fetchConversationMessages,
  sendConversationMessage,
  type Customer,
  type Site,
  type Contract,
  type Incident,
  type Visit,
  type Conversation,
  type Message
} from '../services/api'
import { formatStatus, formatPestType } from '../utils/labels'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'contracts_sites' | 'operations' | 'messages'>('contracts_sites')

// Datos del Cliente
const customer = ref<Customer | null>(null)
const sites = ref<Site[]>([])
const contracts = ref<Contract[]>([])
const incidents = ref<Incident[]>([])
const visits = ref<Visit[]>([])

// Mensajería asociada
const clientConversations = ref<Conversation[]>([])
const selectedConversation = ref<Conversation | null>(null)
const messages = ref<Message[]>([])
const newMessageText = ref('')
const loadingMessages = ref(false)

// Modales de creación
const showSiteModal = ref(false)
const showContractModal = ref(false)
const showEditCustomerModal = ref(false)

// Formularios
const newSite = ref({
  name: '',
  address: '',
  latitude: 36.7212,
  longitude: -4.4214
})

const newContract = ref({
  title: '',
  pest_type: 'COCKROACH',
  frequency: 'monthly',
  amount: 120.0,
  status: 'active',
  next_visit_due: ''
})

const editCustomerForm = ref({
  name: '',
  email: '',
  phone: '',
  customer_type: ''
})

const submittingSite = ref(false)
const submittingContract = ref(false)
const updatingCustomer = ref(false)

// Cargar toda la información del cliente
async function loadCustomerData() {
  loading.value = true
  error.value = null
  try {
    // 1. Obtener datos del cliente
    const custData = await fetchCustomer(props.id)
    customer.value = custData

    // Inicializar formulario de edición
    editCustomerForm.value = {
      name: custData.name,
      email: custData.email,
      phone: custData.phone,
      customer_type: custData.customer_type
    }

    // 2. Obtener locales y contratos en paralelo
    const [sitesData, contractsData, incidentsList, conversationsList] = await Promise.all([
      fetchCustomerSites(props.id),
      fetchCustomerContracts(props.id),
      fetchIncidents({ limit: 500 }),
      fetchConversations(100)
    ])

    sites.value = sitesData
    contracts.value = contractsData

    // 3. Filtrar incidencias de este cliente en local
    // (buscamos por incident.customer_id o indirectamente)
    incidents.value = incidentsList.filter(
      (inc: any) => inc.customer_id === props.id
    )

    // 4. Obtener visitas asociadas a estas incidencias
    const visitsList = await fetchVisits({ limit: 500 })
    const incidentIds = new Set(incidents.value.map(i => i.id))
    visits.value = visitsList.filter(v => incidentIds.has(v.incident_id))

    // 5. Filtrar conversaciones asociadas a este cliente
    clientConversations.value = conversationsList.filter(
      (conv: any) => conv.customer_id === props.id
    )

    if (clientConversations.value.length > 0) {
      selectedConversation.value = clientConversations.value[0]
      await loadConversationMessages(selectedConversation.value.id)
    }

  } catch (err: any) {
    error.value = err?.message || 'Error cargando el workspace del cliente.'
  } finally {
    loading.value = false
  }
}

// Cargar mensajes de chat
async function loadConversationMessages(convId: string) {
  loadingMessages.value = true
  try {
    const list = await fetchConversationMessages(convId)
    messages.value = list
  } catch (err) {
    console.error('Error cargando mensajes:', err)
  } finally {
    loadingMessages.value = false
  }
}

// Cambiar de conversación
async function selectConversation(conv: Conversation) {
  selectedConversation.value = conv
  await loadConversationMessages(conv.id)
}

// Enviar un mensaje outbound
async function handleSendMessage() {
  if (!selectedConversation.value || !newMessageText.value.trim()) return
  try {
    const sent = await sendConversationMessage(
      selectedConversation.value.id,
      newMessageText.value
    )
    messages.value.push(sent)
    newMessageText.value = ''
  } catch (err: any) {
    alert(err?.message || 'No se pudo enviar el mensaje.')
  }
}

// Registrar Local
async function handleCreateSite() {
  if (!newSite.value.name.trim() || !newSite.value.address.trim()) return
  submittingSite.value = true
  try {
    const created = await createSiteForCustomer()
    sites.value.push(created)
    showSiteModal.value = false
    newSite.value = {
      name: '',
      address: '',
      latitude: 36.7212,
      longitude: -4.4214
    }
  } catch (err: any) {
    alert(err?.message || 'Error al crear el local.')
  } finally {
    submittingSite.value = false
  }
}

async function createSiteForCustomer(): Promise<Site> {
  return createCustomerSite(props.id, {
    customer_id: props.id,
    name: newSite.value.name,
    address: newSite.value.address,
    latitude: Number(newSite.value.latitude),
    longitude: Number(newSite.value.longitude)
  })
}

// Registrar Contrato
async function handleCreateContract() {
  if (!newContract.value.title.trim()) return
  submittingContract.value = true
  try {
    const created = await createContractForCustomer()
    contracts.value.push(created)
    showContractModal.value = false
    newContract.value = {
      title: '',
      pest_type: 'COCKROACH',
      frequency: 'monthly',
      amount: 120.0,
      status: 'active',
      next_visit_due: ''
    }
  } catch (err: any) {
    alert(err?.message || 'Error al registrar el contrato.')
  } finally {
    submittingContract.value = false
  }
}

async function createContractForCustomer(): Promise<Contract> {
  return createCustomerContract(props.id, {
    customer_id: props.id,
    title: newContract.value.title,
    pest_type: newContract.value.pest_type,
    frequency: newContract.value.frequency,
    amount: Number(newContract.value.amount),
    status: newContract.value.status,
    next_visit_due: newContract.value.next_visit_due || null
  })
}

// Actualizar datos del cliente
async function handleUpdateCustomer() {
  if (!editCustomerForm.value.name.trim()) return
  updatingCustomer.value = true
  try {
    const updated = await updateCustomer(props.id, {
      name: editCustomerForm.value.name,
      email: editCustomerForm.value.email,
      phone: editCustomerForm.value.phone,
      customer_type: editCustomerForm.value.customer_type
    })
    customer.value = updated
    showEditCustomerModal.value = false
  } catch (err: any) {
    alert(err?.message || 'Error al actualizar datos del cliente.')
  } finally {
    updatingCustomer.value = false
  }
}

// Helpers visuales
function translateCustomerType(type: string): string {
  const mapping: Record<string, string> = {
    HOSPITALITY: 'Hostelería / Restauración',
    FOOD_BUSINESS: 'Industria Alimentaria',
    COMMUNITY: 'Comunidad de Vecinos',
    PRIVATE_HOME: 'Particular / Hogar',
    INDUSTRIAL: 'Polígono / Industrial',
    UNKNOWN: 'No clasificado'
  }
  return mapping[type] || type
}

function getCustomerTypeClass(type: string): string {
  const mapping: Record<string, string> = {
    HOSPITALITY: 'badge-hospitality',
    FOOD_BUSINESS: 'badge-food',
    COMMUNITY: 'badge-community',
    PRIVATE_HOME: 'badge-home',
    INDUSTRIAL: 'badge-industrial',
    UNKNOWN: 'badge-unknown'
  }
  return mapping[type] || ''
}

function translateFrequency(freq: string): string {
  const mapping: Record<string, string> = {
    weekly: 'Semanal',
    monthly: 'Mensual',
    quarterly: 'Trimestral',
    annually: 'Anual'
  }
  return mapping[freq] || freq
}

function getContractStatusClass(status: string): string {
  return status === 'active' ? 'contract-active' : 'contract-inactive'
}

function openIncident(id: string) {
  void router.push(`/incidents/${encodeURIComponent(id)}`)
}

function openVisit(id: string) {
  void router.push(`/visits/${encodeURIComponent(id)}`)
}

function formatDate(isoString?: string | null): string {
  if (!isoString) return 'Sin fecha'
  return new Date(isoString).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  void loadCustomerData()
})
</script>

<template>
  <div class="customer-workspace">
    <div class="workspace-nav-header">
      <button class="secondaryButton back-btn" type="button" @click="router.push('/customers')">
        <svg class="back-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Volver a Clientes
      </button>
      <PageHeader
        v-if="customer"
        :title="customer.name"
        :subtitle="`Workspace 360° • Localizaciones, Contratos y Operaciones de Control de Plagas.`"
      />
    </div>

    <LoadingState v-if="loading" message="Cargando entorno 360° del cliente..." />
    <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
    <div v-else-if="customer" class="detailLayout">

      <!-- Columna Principal (Izquierda): Operaciones, Contratos, Locales y Chat -->
      <div class="main-column">
        <!-- Pestañas de Navegación del Workspace -->
        <div class="workspace-tabs">
          <button
            :class="{ 'active': activeTab === 'contracts_sites' }"
            @click="activeTab = 'contracts_sites'"
            class="tab-btn"
          >
            Locales & Contratos
          </button>
          <button
            :class="{ 'active': activeTab === 'operations' }"
            @click="activeTab = 'operations'"
            class="tab-btn"
          >
            Operaciones ({{ incidents.length }} Casos, {{ visits.length }} Visitas)
          </button>
          <button
            :class="{ 'active': activeTab === 'messages' }"
            @click="activeTab = 'messages'"
            class="tab-btn"
          >
            Mensajería Omnicanal ({{ clientConversations.length }})
          </button>
        </div>

        <!-- Contenido de Pestaña: Locales y Contratos -->
        <div v-if="activeTab === 'contracts_sites'" class="tab-content">
          <!-- CONTRATOS PREVENTIVOS -->
          <div class="section-container">
            <div class="sectionHeader">
              <div class="section-title-group">
                <h3>Contratos de Mantenimiento Preventivo</h3>
                <p class="section-subtitle">Acuerdos de tratamiento recurrente e inspecciones planificadas.</p>
              </div>
              <button class="primaryButton" type="button" @click="showContractModal = true">
                Nuevo Contrato
              </button>
            </div>

            <div v-if="contracts.length === 0" class="empty-section">
              <p>No hay contratos de mantenimiento preventivo registrados para este cliente.</p>
            </div>
            <div v-else class="contracts-grid">
              <div v-for="contract in contracts" :key="contract.id" class="contract-card-item">
                <div class="contract-header">
                  <span class="badge" :class="getContractStatusClass(contract.status)">
                    {{ contract.status === 'active' ? 'Activo' : 'Inactivo' }}
                  </span>
                  <span class="contract-amount">{{ contract.amount.toFixed(2) }}€/mes</span>
                </div>
                <h4 class="contract-title">{{ contract.title }}</h4>
                <div class="contract-details">
                  <div class="detail-row">
                    <span class="lbl">Plaga Objetivo:</span>
                    <span class="val">{{ formatPestType(contract.pest_type) }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="lbl">Frecuencia:</span>
                    <span class="val">{{ translateFrequency(contract.frequency) }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="lbl">Próxima Visita:</span>
                    <span class="val text-amber">{{ contract.next_visit_due ? formatDate(contract.next_visit_due).split(' ')[0] : 'Por determinar' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- LOCALES DE SERVICIO -->
          <div class="section-container" style="margin-top: 24px;">
            <div class="sectionHeader">
              <div class="section-title-group">
                <h3>Locales y Puntos de Control</h3>
                <p class="section-subtitle">Establecimientos físicos geolocalizados donde se ejecutan las visitas.</p>
              </div>
              <button class="primaryButton" type="button" @click="showSiteModal = true">
                Registrar Local
              </button>
            </div>

            <div v-if="sites.length === 0" class="empty-section">
              <p>No hay locales registrados para este cliente.</p>
            </div>
            <div v-else class="tableShell">
              <table class="compactTable">
                <thead>
                  <tr>
                    <th>Nombre del Local</th>
                    <th>Dirección</th>
                    <th>Coordenadas Geográficas</th>
                    <th>Mapa rápido</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="site in sites" :key="site.id">
                    <td><strong>{{ site.name }}</strong></td>
                    <td>{{ site.address }}</td>
                    <td>
                      <span class="coordinates-badge">
                        {{ site.latitude.toFixed(4) }}, {{ site.longitude.toFixed(4) }}
                      </span>
                    </td>
                    <td>
                      <a
                        :href="`https://www.google.com/maps/search/?api=1&query=${site.latitude},${site.longitude}`"
                        target="_blank"
                        class="linkButton"
                      >
                        Ver en Google Maps
                      </a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Contenido de Pestaña: Operaciones -->
        <div v-if="activeTab === 'operations'" class="tab-content">
          <!-- INCIDENCIAS / CASOS -->
          <div class="section-container">
            <h3>Historial de Incidencias / Casos</h3>
            <p class="section-subtitle">Casos reportados o generados por mantenimiento en esta cuenta.</p>

            <div v-if="incidents.length === 0" class="empty-section">
              <p>No se registran incidencias activas ni históricas.</p>
            </div>
            <div v-else class="tableShell">
              <table class="compactTable">
                <thead>
                  <tr>
                    <th>Caso ID</th>
                    <th>Plaga</th>
                    <th>Área afectada</th>
                    <th>Prioridad</th>
                    <th>Estado</th>
                    <th>Creado el</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="inc in incidents" :key="inc.id">
                    <td><span class="mono-id">{{ inc.id.substring(0, 8) }}...</span></td>
                    <td><strong>{{ formatPestType(inc.pest_type) }}</strong></td>
                    <td>{{ inc.affected_area || 'General' }}</td>
                    <td>
                      <span class="badge" :class="`priority-${(inc.operational_priority || inc.priority || '').toLowerCase()}`">
                        {{ inc.operational_priority || inc.priority }}
                      </span>
                    </td>
                    <td>
                      <span class="badge status">
                        {{ formatStatus(inc.status) }}
                      </span>
                    </td>
                    <td>{{ formatDate(inc.created_at) }}</td>
                    <td>
                      <button class="secondaryButton" type="button" @click="openIncident(inc.id)">
                        Gestionar Caso
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- HISTORIAL DE VISITAS -->
          <div class="section-container" style="margin-top: 24px;">
            <h3>Visitas Técnicas Programadas</h3>
            <p class="section-subtitle">Programación de tratamientos preventivos y correctivos.</p>

            <div v-if="visits.length === 0" class="empty-section">
              <p>No se registran visitas programadas o históricas para el cliente.</p>
            </div>
            <div v-else class="tableShell">
              <table class="compactTable">
                <thead>
                  <tr>
                    <th>Visita ID</th>
                    <th>Fecha Inicio</th>
                    <th>Dirección de Visita</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="visit in visits" :key="visit.id">
                    <td><span class="mono-id">{{ visit.id.substring(0, 8) }}...</span></td>
                    <td class="text-emerald"><strong>{{ formatDate(visit.scheduled_start) }}</strong></td>
                    <td>{{ visit.address || 'Local del cliente' }}</td>
                    <td>
                      <span class="badge" :class="visit.status === 'completed' ? 'contract-active' : 'agreement-neutral'">
                        {{ formatStatus(visit.status) }}
                      </span>
                    </td>
                    <td>
                      <button class="secondaryButton" type="button" @click="openVisit(visit.id)">
                        Ver Visita
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Contenido de Pestaña: Mensajería Omnicanal -->
        <div v-if="activeTab === 'messages'" class="tab-content">
          <div class="chat-workspace">
            <!-- Selector de Conversaciones de este cliente -->
            <div class="conversations-sidebar">
              <h4>Conversaciones</h4>
              <div v-if="clientConversations.length === 0" class="empty-list-chat">
                <span>Sin canales activos</span>
              </div>
              <div v-else class="chat-list">
                <button
                  v-for="conv in clientConversations"
                  :key="conv.id"
                  :class="{ 'active': selectedConversation?.id === conv.id }"
                  @click="selectConversation(conv)"
                  class="chat-select-btn"
                >
                  <span class="channel-badge">{{ conv.channel }}</span>
                  <span class="channel-id">{{ conv.contact_identifier }}</span>
                </button>
              </div>
            </div>

            <!-- Panel de Chat Activo -->
            <div class="chat-main">
              <div v-if="!selectedConversation" class="empty-chat-feed">
                <p>Selecciona una conversación del cliente para chatear.</p>
              </div>
              <div v-else class="chat-feed-container">
                <div class="chat-feed-header">
                  <strong>Canal: {{ selectedConversation.channel }}</strong>
                  <span class="channel-detail">{{ selectedConversation.contact_identifier }}</span>
                </div>

                <div class="chat-messages-scroll">
                  <LoadingState v-if="loadingMessages" message="Cargando mensajes..." />
                  <div v-else-if="messages.length === 0" class="no-messages">
                    No hay mensajes en esta conversación.
                  </div>
                  <div
                    v-else
                    v-for="msg in messages"
                    :key="msg.id || ''"
                    :class="['message-bubble-wrapper', msg.direction === 'outbound' ? 'outbound-wrapper' : 'inbound-wrapper']"
                  >
                    <div :class="['message-bubble', msg.direction === 'outbound' ? 'outbound-bubble' : 'inbound-bubble']">
                      <p class="bubble-text">{{ msg.text }}</p>
                      <span class="bubble-time">{{ formatDate(msg.created_at).split(' ')[1] }}</span>
                    </div>
                  </div>
                </div>

                <!-- Input para responder -->
                <form @submit.prevent="handleSendMessage" class="chat-input-form">
                  <input
                    v-model="newMessageText"
                    type="text"
                    placeholder="Escribe un mensaje de respuesta..."
                    required
                  />
                  <button class="primaryButton send-chat-btn" type="submit">
                    Enviar
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Columna Derecha (Estrecha): Perfil del Cliente y Acciones -->
      <div class="sidebar-column">
        <div class="detailPanel">
          <div class="profile-header">
            <span class="badge" :class="getCustomerTypeClass(customer.customer_type)">
              {{ translateCustomerType(customer.customer_type) }}
            </span>
            <button class="secondaryButton edit-profile-btn" type="button" @click="showEditCustomerModal = true">
              Editar Perfil
            </button>
          </div>

          <h3 class="profile-name">{{ customer.name }}</h3>

          <dl class="profile-meta-list">
            <div>
              <dt>Correo Electrónico</dt>
              <dd>{{ customer.email || 'No registrado' }}</dd>
            </div>
            <div>
              <dt>Teléfono</dt>
              <dd>{{ customer.phone || 'No registrado' }}</dd>
            </div>
            <div>
              <dt>Fecha de Registro</dt>
              <dd>{{ formatDate(customer.created_at).split(' ')[0] }}</dd>
            </div>
          </dl>
        </div>

        <div class="detailPanel stats-panel" style="margin-top: 18px;">
          <h3>Resumen Operativo</h3>
          <dl class="stats-list">
            <div class="stat-row">
              <span class="stat-label">Locales</span>
              <span class="stat-value">{{ sites.length }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Contratos</span>
              <span class="stat-value text-emerald">{{ contracts.length }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Casos Totales</span>
              <span class="stat-value">{{ incidents.length }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Mensajería Activa</span>
              <span class="stat-value text-cyan">{{ clientConversations.length }} canales</span>
            </div>
          </dl>
        </div>
      </div>

    </div>

    <!-- Modal: Registrar Local -->
    <div v-if="showSiteModal" class="modal-overlay" @click.self="showSiteModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Registrar Local</h3>
          <button class="close-btn" type="button" @click="showSiteModal = false">&times;</button>
        </div>
        <form @submit.prevent="handleCreateSite" class="modal-form">
          <label>
            Nombre del Local
            <input v-model="newSite.name" type="text" placeholder="Ej. Sucursal Centro, Almacén Principal..." required />
          </label>
          <label>
            Dirección Completa
            <input v-model="newSite.address" type="text" placeholder="Ej. Calle Larios 12, Málaga" required />
          </label>
          <div class="inline-grid-inputs">
            <label>
              Latitud
              <input v-model="newSite.latitude" type="number" step="any" required />
            </label>
            <label>
              Longitud
              <input v-model="newSite.longitude" type="number" step="any" required />
            </label>
          </div>
          <div class="modal-actions">
            <button class="secondaryButton" type="button" @click="showSiteModal = false">Cancelar</button>
            <button class="primaryButton" type="submit" :disabled="submittingSite">
              {{ submittingSite ? 'Guardando...' : 'Crear Local' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Registrar Contrato -->
    <div v-if="showContractModal" class="modal-overlay" @click.self="showContractModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Crear Contrato Preventivo</h3>
          <button class="close-btn" type="button" @click="showContractModal = false">&times;</button>
        </div>
        <form @submit.prevent="handleCreateContract" class="modal-form">
          <label>
            Título del Plan
            <input v-model="newContract.title" type="text" placeholder="Ej. Control de Cucarachas Bar Pepe" required />
          </label>
          <label>
            Plaga Objetivo
            <select v-model="newContract.pest_type">
              <option value="COCKROACH">Cucarachas</option>
              <option value="RODENT">Roedores</option>
              <option value="ANT">Hormigas</option>
              <option value="FLYING_INSECT">Insectos voladores</option>
              <option value="STORED_PRODUCT_INSECT">Insectos en producto</option>
              <option value="UNKNOWN">Otras / Varias</option>
            </select>
          </label>
          <div class="inline-grid-inputs">
            <label>
              Frecuencia
              <select v-model="newContract.frequency">
                <option value="weekly">Semanal</option>
                <option value="monthly">Mensual</option>
                <option value="quarterly">Trimestral</option>
                <option value="annually">Anual</option>
              </select>
            </label>
            <label>
              Monto Mensual (€)
              <input v-model="newContract.amount" type="number" step="0.01" required />
            </label>
          </div>
          <label>
            Próxima Visita Límite
            <input v-model="newContract.next_visit_due" type="date" />
          </label>
          <div class="modal-actions">
            <button class="secondaryButton" type="button" @click="showContractModal = false">Cancelar</button>
            <button class="primaryButton" type="submit" :disabled="submittingContract">
              {{ submittingContract ? 'Guardando...' : 'Crear Contrato' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Cliente -->
    <div v-if="showEditCustomerModal" class="modal-overlay" @click.self="showEditCustomerModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Editar Perfil de Cliente</h3>
          <button class="close-btn" type="button" @click="showEditCustomerModal = false">&times;</button>
        </div>
        <form @submit.prevent="handleUpdateCustomer" class="modal-form">
          <label>
            Nombre / Razón Social
            <input v-model="editCustomerForm.name" type="text" required />
          </label>
          <label>
            Correo Electrónico
            <input v-model="editCustomerForm.email" type="email" />
          </label>
          <label>
            Teléfono
            <input v-model="editCustomerForm.phone" type="tel" />
          </label>
          <label>
            Tipo de Local
            <select v-model="editCustomerForm.customer_type">
              <option value="HOSPITALITY">Hostelería / Restauración</option>
              <option value="FOOD_BUSINESS">Industria Alimentaria</option>
              <option value="COMMUNITY">Comunidad de Vecinos</option>
              <option value="PRIVATE_HOME">Particular / Hogar</option>
              <option value="INDUSTRIAL">Polígono / Industrial</option>
              <option value="UNKNOWN">No Clasificado</option>
            </select>
          </label>
          <div class="modal-actions">
            <button class="secondaryButton" type="button" @click="showEditCustomerModal = false">Cancelar</button>
            <button class="primaryButton" type="submit" :disabled="updatingCustomer">
              {{ updatingCustomer ? 'Guardando...' : 'Guardar Cambios' }}
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<style scoped>
.customer-workspace {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.workspace-nav-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.back-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
}

.back-icon {
  width: 14px;
  height: 14px;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Tabs del Workspace */
.workspace-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #27272a;
  padding-bottom: 2px;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #a1a1aa;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #e4e4e7;
}

.tab-btn.active {
  color: #34d399;
  border-bottom-color: #34d399;
}

/* Contenido de Pestañas */
.tab-content {
  margin-top: 10px;
}

.section-container {
  background: rgba(24, 24, 27, 0.4);
  border: 1px solid #1f1f23;
  border-radius: 12px;
  padding: 20px;
}

.section-title-group h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 800;
  color: #f4f4f5;
}

.section-subtitle {
  margin: 0;
  font-size: 12px;
  color: #71717a;
}

.empty-section {
  padding: 30px;
  text-align: center;
  color: #71717a;
  background: #09090b;
  border: 1px dashed #27272a;
  border-radius: 8px;
  font-size: 13px;
}

/* Grilla de Contratos */
.contracts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.contract-card-item {
  background: #09090b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contract-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.contract-amount {
  font-size: 15px;
  font-weight: 800;
  color: #34d399;
}

.contract-title {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: #e4e4e7;
}

.contract-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
}

.lbl {
  color: #71717a;
}

.val {
  font-weight: 700;
  color: #d4d4d8;
}

.coordinates-badge {
  font-family: 'JetBrains Mono', monospace;
  background: #09090b;
  border: 1px solid #27272a;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: #38bdf8;
}

.mono-id {
  font-family: 'JetBrains Mono', monospace;
  color: #71717a;
}

/* Chat omnicanal */
.chat-workspace {
  display: grid;
  grid-template-columns: 240px 1fr;
  background: rgba(24, 24, 27, 0.6);
  border: 1px solid #27272a;
  border-radius: 12px;
  height: 520px;
  overflow: hidden;
}

.conversations-sidebar {
  border-right: 1px solid #27272a;
  background: #09090b;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conversations-sidebar h4 {
  margin: 0;
  font-size: 12px;
  text-transform: uppercase;
  color: #71717a;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
}

.chat-select-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: all 0.2s;
}

.chat-select-btn:hover {
  background: rgba(39, 39, 42, 0.5);
}

.chat-select-btn.active {
  background: #18181b;
  border-color: #27272a;
}

.channel-badge {
  font-size: 9px;
  font-weight: 900;
  text-transform: uppercase;
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
  padding: 1px 5px;
  border-radius: 4px;
}

.channel-id {
  font-size: 11px;
  color: #d4d4d8;
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}

.chat-main {
  background: rgba(9, 9, 11, 0.3);
  display: flex;
  flex-direction: column;
}

.chat-feed-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-feed-header {
  padding: 16px;
  border-bottom: 1px solid #27272a;
  background: #09090b;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.channel-detail {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #71717a;
}

.chat-messages-scroll {
  flex-grow: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-bubble-wrapper {
  display: flex;
  width: 100%;
}

.outbound-wrapper {
  justify-content: flex-end;
}

.inbound-wrapper {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.outbound-bubble {
  background: #059669; /* emerald-600 */
  color: white;
  border-bottom-right-radius: 2px;
}

.inbound-bubble {
  background: #27272a; /* zinc-800 */
  color: #e4e4e7;
  border-bottom-left-radius: 2px;
}

.bubble-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.4;
}

.bubble-time {
  font-size: 9px;
  align-self: flex-end;
  opacity: 0.7;
}

.no-messages, .empty-chat-feed, .empty-list-chat {
  color: #71717a;
  text-align: center;
  font-size: 13px;
  padding: 30px;
  margin: auto;
}

.chat-input-form {
  padding: 14px;
  border-top: 1px solid #27272a;
  background: #09090b;
  display: flex;
  gap: 10px;
}

.chat-input-form input {
  flex-grow: 1;
  min-width: 0;
}

.send-chat-btn {
  min-height: 40px;
}

/* Panel lateral del perfil */
.sidebar-column {
  display: flex;
  flex-direction: column;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.profile-name {
  margin: 0 0 16px 0;
  font-size: 20px;
  font-weight: 900;
  color: #f4f4f5;
}

.profile-meta-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 0;
}

/* Badges específicos de tipos */
.badge-hospitality { background: rgba(139, 92, 246, 0.15); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.2); }
.badge-food { background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.2); }
.badge-community { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.2); }
.badge-home { background: rgba(45, 212, 191, 0.15); color: #2dd4bf; border: 1px solid rgba(45, 212, 191, 0.2); }
.badge-industrial { background: rgba(249, 115, 22, 0.15); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.2); }
.badge-unknown { background: rgba(113, 113, 122, 0.15); color: #a1a1aa; border: 1px solid rgba(113, 113, 122, 0.2); }

.contract-active { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); }
.contract-inactive { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }

.stats-panel h3 {
  margin: 0 0 16px 0;
  font-size: 14px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  font-weight: 800;
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.stat-label {
  color: #a1a1aa;
}

.stat-value {
  font-weight: 700;
  color: #e4e4e7;
}

.inline-grid-inputs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

/* Modales */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.close-btn {
  background: transparent;
  border: 0;
  color: #a1a1aa;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-form label {
  gap: 6px;
}

.modal-form input,
.modal-form select {
  width: 100%;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}
</style>
