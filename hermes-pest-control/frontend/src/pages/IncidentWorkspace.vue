<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchIncident,
  fetchVisits,
  fetchDocuments,
  fetchTechnicians,
  createVisit,
  updateIncident,
  updateDocument,
  generateIncidentSummaryDocument,
  isUnauthorizedError,
  INCIDENT_STATUSES,
  INCIDENT_PRIORITIES,
  VISIT_STATUSES,
  fetchCustomer,
  fetchDocumentVersions,
  createDocumentVersion,
  type Incident,
  type IncidentStatus,
  type IncidentPriority,
  type Visit,
  type VisitStatus,
  type OperationalDocument,
  type Technician,
  type OperationalDocumentVersion,
} from '../services/api'
import {
  formatStatus,
  formatPriority,
  formatPestType,
  formatSeverity,
  formatSlaStatus,
  formatVisitType,
  formatTechnicianLevel,
} from '../utils/labels'

import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import CaseTimeline from '../components/dashboard/CaseTimeline.vue'

const props = defineProps<{
  id: string
}>()

const router = useRouter()

const incident = ref<Incident | null>(null)
const visits = ref<Visit[]>([])
const documents = ref<OperationalDocument[]>([])
const technicians = ref<Technician[]>([])

// Loading y Errores
const loading = ref(false)
const saving = ref(false)
const visitSaving = ref(false)
const docGenerating = ref(false)
const docSaving = ref(false)
const error = ref<string | null>(null)

// Formularios
const formStatus = ref<IncidentStatus>('pending_review')
const formPriority = ref<IncidentPriority>('medium')
const formInternalNotes = ref('')

// Programación de Visita
const visitTechnicianId = ref('')
const visitScheduledStart = ref('')
const visitScheduledEnd = ref('')
const visitStatus = ref<VisitStatus>('draft')
const visitAddress = ref('')
const visitNotes = ref('')
const visitSuccessMsg = ref(false)

// Chat interactivo simulado
const chatInput = ref('')
const localChatMessages = ref<{ sender: 'client' | 'hermes' | 'supervisor', name: string, text: string, time: string }[]>([])

// Documento Activo en Editor (Briefs versionados)
const selectedDoc = ref<OperationalDocument | null>(null)
const editingDocContent = ref('')
const selectedDocVersion = ref<number | string>('current')
const versions = ref<OperationalDocumentVersion[]>([])
const customerName = ref<string | null>(null)

// Cargar versiones reales del documento
async function loadDocVersions(docId: string) {
  try {
    const list = await fetchDocumentVersions(docId)
    versions.value = list
  } catch (err) {
    console.error('Error cargando versiones reales del documento:', err)
  }
}

// Cargar Datos
async function loadAllData() {
  loading.value = true
  error.value = null
  customerName.value = null
  try {
    const loadedIncident = await fetchIncident(props.id)
    incident.value = loadedIncident

    // Sincronizar formulario
    formStatus.value = (loadedIncident.status as IncidentStatus) || 'pending_review'
    formPriority.value = (loadedIncident.priority as IncidentPriority) || 'medium'
    formInternalNotes.value = loadedIncident.internal_notes || ''
    visitAddress.value = loadedIncident.location || ''

    // Si tiene cliente, cargar su perfil de cliente
    if (loadedIncident.customer_id) {
      try {
        const cust = await fetchCustomer(loadedIncident.customer_id)
        customerName.value = cust.name
      } catch (err) {
        console.error('Error cargando cliente de la incidencia:', err)
      }
    }

    // Cargar Visitas, Documentos y Técnicos
    const [loadedVisits, loadedDocs, loadedTechs] = await Promise.all([
      fetchVisits({ incident_id: props.id, limit: 100 }),
      fetchDocuments({ incident_id: props.id, limit: 100 }),
      fetchTechnicians({ active: true, limit: 200 })
    ])

    visits.value = loadedVisits
    documents.value = loadedDocs
    technicians.value = loadedTechs

    // Si hay un documento de tipo brief_tecnico o summary, seleccionarlo por defecto
    if (loadedDocs.length > 0) {
      selectedDoc.value = loadedDocs[0]
      editingDocContent.value = loadedDocs[0].content
      selectedDocVersion.value = 'current'
      await loadDocVersions(loadedDocs[0].id)
    }

    // Inicializar chat simulado
    initChat(loadedIncident)

  } catch (err) {
    if (isUnauthorizedError(err)) {
      void router.push('/login')
      return
    }
    error.value = err instanceof Error ? err.message : 'Error cargando la consola de operaciones'
  } finally {
    loading.value = false
  }
}

// Inicializar chat simulado contextual
function initChat(inc: Incident) {
  const clientName = inc.location || 'Cliente'
  const pest = formatPestType(inc.pest_type)
  const channel = inc.channel || 'Telegram'
  const dateStr = inc.created_at
    ? new Date(inc.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    : '12:01'

  const channelText = channel.toUpperCase() === 'EMAIL' ? 'correo electrónico' : channel.toUpperCase() === 'WEB' ? 'formulario web' : channel

  localChatMessages.value = [
    {
      sender: 'client',
      name: 'Contacto Cliente',
      text: `Buenas, escribo desde ${clientName}. Hemos detectado indicios de ${pest} en la zona de ${inc.affected_area || 'almacén y cocina'}. Necesitamos un técnico lo antes posible. Gracias.`,
      time: dateStr,
    },
    {
      sender: 'hermes',
      name: 'Hermes IA',
      text: `Hola. He recibido tu mensaje a través de nuestro canal de ${channelText}. Analizando la gravedad del caso en ${clientName}...`,
      time: dateStr,
    },
    {
      sender: 'hermes',
      name: 'Hermes IA',
      text: `Incidencia de nivel de prioridad ${inc.priority.toUpperCase()} creada con éxito en el Centro Operativo. Se ha activado un SLA de respuesta de ${inc.sla_hours || 4} horas. Un supervisor y un técnico serán asignados de inmediato.`,
      time: dateStr,
    }
  ]
}

// Enviar mensaje en chat simulado
function sendSupervisorMessage() {
  if (!chatInput.value.trim()) return
  const now = new Date()
  const timeStr = now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })

  localChatMessages.value.push({
    sender: 'supervisor',
    name: 'Supervisor (Tú)',
    text: chatInput.value.trim(),
    time: timeStr
  })

  const textSent = chatInput.value.trim()
  chatInput.value = ''

  // Respuesta automática simulada de Hermes o cliente
  setTimeout(() => {
    localChatMessages.value.push({
      sender: 'hermes',
      name: 'Hermes IA',
      text: `Comando recibido. Actualizando canal de comunicación con notas: "${textSent}".`,
      time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    })
  }, 1000)
}

// Guardar Incidencia (Estado / Prioridad)
async function handleSaveIncident() {
  saving.value = true
  try {
    await updateIncident(props.id, {
      status: formStatus.value,
      priority: formPriority.value,
      internal_notes: formInternalNotes.value,
    })
    // Recargar datos
    const loadedIncident = await fetchIncident(props.id)
    incident.value = loadedIncident
  } catch (err) {
    console.error('Error al guardar incidencia:', err)
  } finally {
    saving.value = false
  }
}

// Programar Visita
async function handleCreateVisit() {
  visitSaving.value = true
  visitSuccessMsg.value = false
  try {
    await createVisit({
      incident_id: props.id,
      technician_id: visitTechnicianId.value || null,
      scheduled_start: visitScheduledStart.value || null,
      scheduled_end: visitScheduledEnd.value || null,
      status: visitStatus.value,
      address: visitAddress.value.trim() || null,
      notes: visitNotes.value.trim() || null,
    })
    visitTechnicianId.value = ''
    visitScheduledStart.value = ''
    visitScheduledEnd.value = ''
    visitStatus.value = 'draft'
    visitNotes.value = ''
    visitSuccessMsg.value = true

    // Recargar visitas
    visits.value = await fetchVisits({ incident_id: props.id, limit: 100 })
  } catch (err) {
    console.error('Error al crear visita:', err)
  } finally {
    visitSaving.value = false
  }
}

// Generar Resumen IA
async function handleGenerateSummary() {
  docGenerating.value = true
  try {
    await generateIncidentSummaryDocument(props.id)
    documents.value = await fetchDocuments({ incident_id: props.id, limit: 100 })
    if (documents.value.length > 0) {
      selectedDoc.value = documents.value[0]
      editingDocContent.value = documents.value[0].content
      selectedDocVersion.value = 'current'
    }
  } catch (err) {
    console.error('Error al generar resumen IA:', err)
  } finally {
    docGenerating.value = false
  }
}

// --- Epic 6: Documentos Vivos ---
const docVersions = computed(() => {
  return versions.value
})

// Cambiar la versión visualizada
function handleVersionChange() {
  if (!selectedDoc.value) return
  if (selectedDocVersion.value === 'current') {
    editingDocContent.value = selectedDoc.value.content
  } else {
    const verNum = Number(selectedDocVersion.value)
    const verData = versions.value.find(v => v.version_number === verNum)
    if (verData) {
      editingDocContent.value = verData.content
    }
  }
}

// Guardar nueva versión del documento
async function handleSaveNewVersion() {
  if (!selectedDoc.value) return
  docSaving.value = true

  try {
    // 1. Guardar la versión real en base de datos
    await createDocumentVersion(selectedDoc.value.id, editingDocContent.value, 'admin')

    // 2. Actualizar el documento principal
    const updated = await updateDocument(selectedDoc.value.id, {
      content: editingDocContent.value
    })

    selectedDoc.value = updated
    editingDocContent.value = updated.content
    selectedDocVersion.value = 'current'

    // 3. Recargar versiones y documentos del caso
    await loadDocVersions(selectedDoc.value.id)
    documents.value = await fetchDocuments({ incident_id: props.id, limit: 100 })
  } catch (err) {
    console.error('Error al guardar versión:', err)
  } finally {
    docSaving.value = false
  }
}

// Restaurar versión antigua como la versión activa
async function handleRestoreVersion() {
  if (!selectedDoc.value || selectedDocVersion.value === 'current') return
  const verNum = Number(selectedDocVersion.value)
  const verData = versions.value.find(v => v.version_number === verNum)
  if (!verData) return

  editingDocContent.value = verData.content
  await handleSaveNewVersion()
}

// Cálculos de SLA
const slaPercentage = computed(() => {
  if (!incident.value || !incident.value.sla_hours) return 0
  const elapsed = incident.value.elapsed_hours || 0
  const total = incident.value.sla_hours
  const percentage = Math.min(100, Math.max(0, (elapsed / total) * 100))
  return parseFloat(percentage.toFixed(0))
})

const slaColorClass = computed(() => {
  const p = slaPercentage.value
  if (incident.value?.sla_status?.toLowerCase().includes('breach')) return 'bar-breached'
  if (p >= 80) return 'bar-danger'
  if (p >= 50) return 'bar-warning'
  return 'bar-success'
})

const getTechnicianName = (techId: string | null | undefined) => {
  if (!techId) return 'Sin asignar'
  return technicians.value.find(t => t.id === techId)?.name || 'Técnico'
}

onMounted(() => {
  void loadAllData()
})
</script>

<template>
  <div class="incident-workspace-page">
    <Breadcrumbs
      parentPath="/incidents"
      parentLabel="Incidencias"
      currentLabel="Consola Operativa 360°"
    />

    <div v-if="loading" class="workspace-loading">Cargando consola operativa...</div>
    <div v-else-if="error" class="workspace-error">{{ error }}</div>

    <div v-else-if="incident" class="workspace-layout">

      <!-- COLUMNA 1: Datos Cliente & Ficha Técnica (SLA, Formulario) -->
      <aside class="workspace-col col-sidebar">
         <!-- Panel 1: Cliente & Caso -->
        <section class="workspace-card sidebar-card" aria-label="Ficha de cliente">
          <header class="card-header">
            <span class="card-eyebrow">Intake ID: #{{ incident.id.slice(0, 8).toUpperCase() }}</span>
            <h2 class="card-title">{{ incident.location || 'Localización S/D' }}</h2>
            <div v-if="incident.customer_id" class="customer-link-container" style="margin-top: 6px;">
              <span style="font-size: 11px; color: #71717a;">Cliente: </span>
              <router-link
                :to="`/customers/${incident.customer_id}`"
                class="linkButton"
                style="font-size: 13px; font-weight: 750;"
              >
                {{ customerName || 'Workspace 360°' }}
              </router-link>
            </div>
            <p class="card-desc" v-if="incident.affected_area" style="margin-top: 6px;">📍 Zona: {{ incident.affected_area }}</p>
          </header>

          <div class="card-body">
            <div class="meta-row">
              <span class="meta-label">Plaga</span>
              <span class="pest-badge">{{ formatPestType(incident.pest_type).toUpperCase() }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">Canal Entrada</span>
              <span class="badge channel-badge">{{ incident.channel.toUpperCase() }}</span>
            </div>
            <div class="meta-row" v-if="incident.severity">
              <span class="meta-label">Severidad IA</span>
              <span class="badge" :class="`severity-${incident.severity.toLowerCase()}`">
                {{ formatSeverity(incident.severity) }}
              </span>
            </div>
            <div class="meta-row" v-if="incident.technician_level">
              <span class="meta-label">Nivel Requerido</span>
              <span class="badge font-bold">{{ formatTechnicianLevel(incident.technician_level) }}</span>
            </div>
          </div>
        </section>

        <!-- Panel 1.5: Memoria Conversacional / Reincidencia -->
        <section v-if="incident.metadata?.is_recurrence" class="workspace-card sidebar-card" style="border: 1px solid #ef4444; background: #fef2f2;" aria-label="Alerta de Reincidencia">
          <header class="card-header border-none" style="padding-bottom: 0;">
            <h3 class="card-subtitle" style="color: #b91c1c; display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 16px;">⚠️</span> ALERTA DE REINCIDENCIA
            </h3>
          </header>
          <div class="card-body" style="padding-top: 8px;">
            <p style="font-size: 13px; color: #991b1b; margin-bottom: 8px; line-height: 1.4;">
              El agente inteligente ha detectado que este cliente vuelve a reportar problemas de {{ formatPestType(incident.pest_type) }}.
            </p>
            <div v-if="incident.metadata?.parent_incident_id" style="font-size: 12px;">
              <router-link :to="`/incidents/${incident.metadata.parent_incident_id}`" style="color: #b91c1c; text-decoration: underline; font-weight: 600;">
                Ver caso original anterior
              </router-link>
            </div>
          </div>
        </section>

        <!-- Panel 2: Acuerdo SLA & Respuesta -->
        <section class="workspace-card sidebar-card" aria-label="Monitoreo de SLA">
          <header class="card-header border-none">
            <h3 class="card-subtitle">Control de SLA</h3>
          </header>
          <div class="card-body gap-12">
            <div class="sla-progress-box">
              <div class="progress-bar-bg">
                <div
                  class="progress-bar-fill"
                  :class="slaColorClass"
                  :style="{ width: `${slaPercentage}%` }"
                ></div>
              </div>
              <div class="progress-labels">
                <span>Transcurrido: {{ incident.elapsed_hours || 0 }}h / {{ incident.sla_hours || 0 }}h</span>
                <span class="font-bold">{{ slaPercentage }}%</span>
              </div>
            </div>

            <div class="meta-row">
              <span class="meta-label">Estado SLA</span>
              <span class="badge" :class="`sla-${(incident.sla_status || '').toLowerCase()}`">
                {{ formatSlaStatus(incident.sla_status) }}
              </span>
            </div>
            <div class="meta-row">
              <span class="meta-label">Horas Restantes</span>
              <span class="badge time-tag font-bold">⏰ {{ incident.remaining_hours || 0 }}h</span>
            </div>
          </div>
        </section>

        <!-- Panel 3: Formulario Acciones Operativas -->
        <section class="workspace-card sidebar-card" aria-label="Actualizar caso">
          <header class="card-header border-none">
            <h3 class="card-subtitle">Acciones Operativas</h3>
          </header>
          <form class="card-body form-body" @submit.prevent="handleSaveIncident">
            <label class="form-label">
              Estado del caso
              <select v-model="formStatus" :disabled="saving">
                <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
                  {{ formatStatus(status) }}
                </option>
              </select>
            </label>

            <label class="form-label">
              Prioridad
              <select v-model="formPriority" :disabled="saving">
                <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
                  {{ formatPriority(priority) }}
                </option>
              </select>
            </label>

            <label class="form-label">
              Notas internas del Supervisor
              <textarea
                v-model="formInternalNotes"
                :disabled="saving"
                placeholder="Escribe notas operativas..."
                rows="4"
              ></textarea>
            </label>

            <button class="primaryButton w-full" type="submit" :disabled="saving">
              {{ saving ? 'Guardando...' : 'Aplicar Cambios' }}
            </button>
          </form>
        </section>
      </aside>

      <!-- COLUMNA 2: Chat del Cliente & Línea de Tiempo Unificada -->
      <main class="workspace-col col-main">
        <!-- Panel 1: Conversación de Intake Unificada -->
        <section class="workspace-card chat-card" aria-label="Chat omnicanal">
          <header class="card-header chat-header">
            <div class="chat-meta">
              <span class="chat-icon">💬</span>
              <div>
                <h3 class="card-subtitle">Conversación de Intake</h3>
                <p class="card-desc">Historial en tiempo real de interacción con el cliente</p>
              </div>
            </div>
            <span class="channel-indicator badge channel-badge">{{ incident.channel.toUpperCase() }}</span>
          </header>

          <div class="chat-body-messages">
            <div
              v-for="(msg, idx) in localChatMessages"
              :key="idx"
              class="chat-bubble-wrapper"
              :class="`sender-${msg.sender}`"
            >
              <span class="chat-avatar">{{ msg.sender === 'client' ? '👤' : msg.sender === 'hermes' ? '🤖' : '👨‍💼' }}</span>
              <div class="chat-bubble">
                <span class="bubble-name">{{ msg.name }}</span>
                <p class="bubble-text">{{ msg.text }}</p>
                <time class="bubble-time">⏱️ {{ msg.time }}</time>
              </div>
            </div>
          </div>

          <form class="chat-footer" @submit.prevent="sendSupervisorMessage">
            <input
              v-model="chatInput"
              type="text"
              placeholder="Escribe un mensaje de respuesta del supervisor..."
            />
            <button class="primaryButton" type="submit">Enviar</button>
          </form>
        </section>

        <!-- Panel 2: Línea de Tiempo Único de Caso (Epic 1) -->
        <section class="workspace-card timeline-card" aria-label="Timeline del caso">
          <header class="card-header">
            <h3 class="card-subtitle">Línea de Tiempo del Caso (CaseTimeline)</h3>
            <p class="card-desc">Historial unificado y cruzado de toda la vida operativa del incidente</p>
          </header>
          <div class="card-body scroll-timeline">
            <CaseTimeline
              :incidentId="id"
              :conversationId="incident.conversation_id"
            />
          </div>
        </section>
      </main>

      <!-- COLUMNA 3: Visitas & Documentos Vivos (v1, v2, v3) -->
      <aside class="workspace-col col-actions">
        <!-- Panel 1: Agenda y Visitas Asociadas -->
        <section class="workspace-card visits-card" aria-label="Visitas técnicas">
          <header class="card-header border-none">
            <h3 class="card-subtitle">Visitas del Servicio ({{ visits.length }})</h3>
          </header>
          <div class="card-body gap-16">
            <!-- Mini tabla de visitas -->
            <div v-if="visits.length === 0" class="drawer-empty-msg">
              No hay visitas agendadas para esta incidencia.
            </div>
            <div class="mini-visits-list" v-else>
              <div
                v-for="v in visits"
                :key="v.id"
                class="mini-visit-item"
                @click="router.push(`/visits/${v.id}`)"
              >
                <div class="visit-meta">
                  <span class="visit-tech-name">👤 {{ getTechnicianName(v.technician_id) }}</span>
                  <span class="visit-time font-bold">⏰ {{ v.scheduled_start ? v.scheduled_start.slice(5, 16).replace('T', ' ') : 'S/F' }}</span>
                </div>
                <div class="visit-status-row">
                  <span class="visit-addr">{{ v.address || 'Sin dirección' }}</span>
                  <span class="badge status font-bold">{{ formatStatus(v.status) }}</span>
                </div>
              </div>
            </div>

            <!-- Formulario de creación de visita -->
            <form class="create-visit-form border-top-divider" @submit.prevent="handleCreateVisit">
              <h4>Programar Nueva Visita</h4>
              <label class="form-label">
                Técnico
                <select v-model="visitTechnicianId" :disabled="visitSaving">
                  <option value="">Sin asignar</option>
                  <option v-for="t in technicians" :key="t.id" :value="t.id">
                    {{ t.name }}
                  </option>
                </select>
              </label>

              <div class="form-row">
                <label class="form-label flex-1">
                  Inicio
                  <input v-model="visitScheduledStart" :disabled="visitSaving" type="datetime-local" />
                </label>
                <label class="form-label flex-1">
                  Fin
                  <input v-model="visitScheduledEnd" :disabled="visitSaving" type="datetime-local" />
                </label>
              </div>

              <label class="form-label">
                Dirección
                <input v-model="visitAddress" :disabled="visitSaving" type="text" />
              </label>

              <label class="form-label">
                Notas operativas para el técnico
                <textarea v-model="visitNotes" :disabled="visitSaving" rows="2"></textarea>
              </label>

              <button class="primaryButton w-full" type="submit" :disabled="visitSaving">
                {{ visitSaving ? 'Programando...' : 'Programar Visita' }}
              </button>
              <p v-if="visitSuccessMsg" class="success-msg">¡Visita creada satisfactoriamente!</p>
            </form>
          </div>
        </section>

        <!-- Panel 2: Documentos Vivos & Briefing Técnico (Epic 6) -->
        <section class="workspace-card docs-card" aria-label="Documentos vivos">
          <header class="card-header border-none justify-between items-center flex-row">
            <h3 class="card-subtitle">Documentos Vivos</h3>
            <button
              class="primaryButton font-bold text-xs"
              type="button"
              :disabled="docGenerating"
              @click="handleGenerateSummary"
            >
              {{ docGenerating ? 'Generando...' : '🔄 Re-Generar Brief' }}
            </button>
          </header>

          <div class="card-body gap-12" v-if="selectedDoc">
            <div class="doc-header-meta">
              <span class="font-bold text-sm text-highlight">📄 {{ selectedDoc.title }}</span>

              <!-- Selector de versiones (Epic 6) -->
              <div class="version-selector-container">
                <label class="version-label">Versión:</label>
                <select
                  v-model="selectedDocVersion"
                  class="version-select"
                  @change="handleVersionChange"
                >
                  <option value="current">Actual (v{{ versions.length }})</option>
                  <option
                    v-for="v in versions"
                    :key="v.id"
                    :value="v.version_number"
                  >
                    v{{ v.version_number }} ({{ v.updated_at.slice(5, 16).replace('T', ' ') }})
                  </option>
                </select>
              </div>
            </div>

            <!-- Editor del documento -->
            <div class="doc-editor-wrapper">
              <textarea
                v-model="editingDocContent"
                class="doc-textarea"
                rows="10"
                placeholder="Escribe o modifica el brief del caso..."
              ></textarea>
            </div>

            <div class="doc-actions border-top-divider">
              <button
                class="primaryButton flex-1 font-bold"
                type="button"
                :disabled="docSaving"
                @click="handleSaveNewVersion"
              >
                {{ docSaving ? 'Guardando...' : 'Guardar Nueva Versión' }}
              </button>

              <button
                class="secondaryButton font-bold"
                type="button"
                v-if="selectedDocVersion !== 'current'"
                @click="handleRestoreVersion"
              >
                Restaurar v{{ selectedDocVersion }}
              </button>
            </div>
          </div>

          <div v-else class="card-body text-center py-20 text-zinc-500">
            No se han generado reportes o briefs para este caso.
            <button class="primaryButton mt-12 block mx-auto" type="button" @click="handleGenerateSummary">
              Generar Brief Técnico
            </button>
          </div>
        </section>
      </aside>

    </div>
  </div>
</template>

<style scoped>
.incident-workspace-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100vh;
}

.workspace-loading,
.workspace-error {
  padding: 40px;
  text-align: center;
  color: #71717a;
  font-weight: 700;
}

.workspace-layout {
  display: grid;
  grid-template-columns: 280px 1fr 340px;
  gap: 20px;
  align-items: start;
}

.workspace-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

/* Tarjeta base del Workspace */
.workspace-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  padding: 14px 18px;
  border-bottom: 1px solid #27272a;
  background: #141416;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-header.border-none {
  border-bottom: none;
}

.card-eyebrow {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
}

.card-title {
  font-size: 16px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.card-subtitle {
  font-size: 13px;
  font-weight: 900;
  color: #e4e4e7;
  text-transform: uppercase;
  margin: 0;
  letter-spacing: 0.03em;
}

.card-desc {
  font-size: 11px;
  color: #71717a;
  margin: 0;
  font-weight: 600;
}

.card-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-body {
  gap: 14px;
}

/* Meta filas */
.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.meta-label {
  color: #71717a;
  font-weight: 500;
}

.pest-badge {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}

.channel-badge {
  background: #27272a;
  color: #d4d4d8;
  font-size: 10px;
  font-weight: 800;
}

.time-tag {
  color: #fbbf24;
}

/* SLA Bar */
.sla-progress-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #09090b;
  border-radius: 6px;
  padding: 10px;
  border: 1px solid #1f1f23;
}

.progress-bar-bg {
  height: 6px;
  background: #27272a;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 9999px;
}

.bar-success { background: #10b981; }
.bar-warning { background: #f59e0b; }
.bar-danger { background: #ef4444; }
.bar-breached { background: #7f1d1d; }

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #a1a1aa;
}

/* Chat de Intake */
.chat-card {
  height: 420px;
}

.chat-header {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.chat-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-icon {
  font-size: 24px;
}

.chat-body-messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #09090b;
}

.chat-bubble-wrapper {
  display: flex;
  gap: 10px;
  max-width: 80%;
}

.chat-bubble-wrapper.sender-client {
  align-self: flex-start;
}

.chat-bubble-wrapper.sender-hermes,
.chat-bubble-wrapper.sender-supervisor {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-avatar {
  font-size: 18px;
  background: #18181b;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #27272a;
  flex-shrink: 0;
}

.chat-bubble {
  background: #1c1c1f;
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sender-client .chat-bubble {
  border-top-left-radius: 0;
}

.sender-hermes .chat-bubble {
  border-top-right-radius: 0;
  background: rgba(16, 185, 129, 0.05);
  border-color: rgba(16, 185, 129, 0.2);
}

.sender-supervisor .chat-bubble {
  border-top-right-radius: 0;
  background: rgba(56, 189, 248, 0.05);
  border-color: rgba(56, 189, 248, 0.2);
}

.bubble-name {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
}

.sender-hermes .bubble-name {
  color: #34d399;
}

.sender-supervisor .bubble-name {
  color: #38bdf8;
}

.bubble-text {
  font-size: 12px;
  color: #e4e4e7;
  margin: 0;
  line-height: 1.4;
}

.bubble-time {
  font-size: 9px;
  color: #52525b;
  align-self: flex-end;
}

.chat-footer {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #27272a;
  background: #141416;
}

.chat-footer input {
  flex-grow: 1;
}

/* Timeline Card */
.timeline-card {
  flex-grow: 1;
}

.scroll-timeline {
  max-height: 500px;
  overflow-y: auto;
}

/* Visitas */
.mini-visits-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mini-visit-item {
  background: #09090b;
  border: 1px solid #1f1f23;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.mini-visit-item:hover {
  border-color: #3f3f46;
  background: #121214;
}

.visit-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.visit-tech-name {
  color: #e4e4e7;
}

.visit-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
}

.visit-addr {
  color: #71717a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.create-visit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.create-visit-form h4 {
  font-size: 11px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  margin: 0;
  letter-spacing: 0.05em;
}

.form-row {
  display: flex;
  gap: 12px;
}

.success-msg {
  color: #34d399;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  margin: 0;
}

/* Documentos Vivos */
.doc-header-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #09090b;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #1f1f23;
}

.version-selector-container {
  display: flex;
  align-items: center;
  gap: 6px;
}

.version-label {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
}

.version-select {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  color: #e4e4e7;
  font-weight: 700;
  outline: none;
}

.doc-editor-wrapper {
  background: #09090b;
  border: 1px solid #1f1f23;
  border-radius: 6px;
  overflow: hidden;
}

.doc-textarea {
  width: 100%;
  background: transparent;
  border: none;
  color: #d4d4d8;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 12px;
  resize: vertical;
  outline: none;
}

.doc-actions {
  display: flex;
  gap: 10px;
}

.border-top-divider {
  border-top: 1px solid #27272a;
  padding-top: 14px;
  margin-top: 4px;
}

.text-highlight {
  color: #34d399;
}

@media (max-width: 1280px) {
  .workspace-layout {
    grid-template-columns: 1fr;
  }
}
</style>
