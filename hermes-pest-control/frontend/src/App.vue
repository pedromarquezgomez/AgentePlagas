<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CalendarPanel from './components/CalendarPanel.vue'
import DashboardPanel from './components/DashboardPanel.vue'
import DocumentDetail from './components/DocumentDetail.vue'
import DocumentTable from './components/DocumentTable.vue'
import HumanReviewDetail from './components/HumanReviewDetail.vue'
import HumanReviewTable from './components/HumanReviewTable.vue'
import IncidentDetail from './components/IncidentDetail.vue'
import IncidentTable from './components/IncidentTable.vue'
import LoginPanel from './components/LoginPanel.vue'
import ShadowDecisionDetail from './components/ShadowDecisionDetail.vue'
import ShadowDecisionTable from './components/ShadowDecisionTable.vue'
import TechnicianDetail from './components/TechnicianDetail.vue'
import TechnicianTable from './components/TechnicianTable.vue'
import ToolExecutionDetail from './components/ToolExecutionDetail.vue'
import ToolExecutionTable from './components/ToolExecutionTable.vue'
import VisitDetail from './components/VisitDetail.vue'
import VisitTable from './components/VisitTable.vue'
import {
  AUTH_MODE,
  fetchDashboardSummary,
  fetchDocuments,
  fetchHumanReviewItems,
  fetchIncidents,
  fetchToolExecutionRecords,
  listShadowDecisionRecords,
  fetchTechnicians,
  fetchVisits,
  getStoredAuthIndicator,
  HUMAN_REVIEW_STATUSES,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  isUnauthorizedError,
  loginWithCredentials,
  logoutCurrentUser,
  observeAuthState,
  REQUIRE_LOGIN,
  setStoredAdminApiKey,
  type DashboardSummary,
  type LoginPayload,
  type OperationalDocument,
  type HumanReviewItem,
  type Incident,
  type Technician,
  type ShadowDecisionRecord,
  type Visit,
  type ToolExecutionRecord,
  TOOL_REVIEW_STATUSES,
  VISIT_STATUSES,
} from './services/api'
import {
  formatAction,
  formatChannel,
  formatDocumentType,
  formatPriority,
  formatStatus,
  formatReviewStatus,
  formatRiskLevel,
  formatToolDecision,
  formatToolName,
  formatToolProvider,
} from './utils/labels'

const SHADOW_ACTION_TYPES = ['create_incident', 'collect_missing_data', 'escalate_to_human'] as const
const DOCUMENT_TYPE_OPTIONS = [
  'incident_summary',
  'technician_brief',
  'post_treatment_recommendations',
  'work_report_draft',
] as const

const incidents = ref<Incident[]>([])
const dashboardSummary = ref<DashboardSummary | null>(null)
const reviewItems = ref<HumanReviewItem[]>([])
const technicians = ref<Technician[]>([])
const visits = ref<Visit[]>([])
const documents = ref<OperationalDocument[]>([])
const shadowDecisionRecords = ref<ShadowDecisionRecord[]>([])
const toolExecutionRecords = ref<ToolExecutionRecord[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref('')
const priorityFilter = ref('')
const reviewStatusFilter = ref('')
const reviewPriorityFilter = ref('')
const technicianActiveFilter = ref('')
const visitStatusFilter = ref('')
const visitTechnicianFilter = ref('')
const documentStatusFilter = ref('')
const documentTypeFilter = ref('')
const shadowChannelFilter = ref('')
const shadowActionFilter = ref('')
const shadowLimitFilter = ref('100')
const toolStatusFilter = ref('')
const toolNameFilter = ref('')
const toolProviderFilter = ref('')
const toolDecisionFilter = ref('')
const toolRiskFilter = ref('')
const toolRequiresApprovalFilter = ref('')
const toolLimitFilter = ref('100')
const currentPath = ref(window.location.pathname)
const adminApiKey = ref(getStoredAuthIndicator())
const authMessage = ref<string | null>(null)
let stopAuthObserver: (() => void) | null = null

const hasFilters = computed(() => Boolean(statusFilter.value || priorityFilter.value))
const hasReviewFilters = computed(() => Boolean(reviewStatusFilter.value || reviewPriorityFilter.value))
const hasTechnicianFilters = computed(() => Boolean(technicianActiveFilter.value))
const hasVisitFilters = computed(() => Boolean(visitStatusFilter.value || visitTechnicianFilter.value))
const hasDocumentFilters = computed(() => Boolean(documentStatusFilter.value || documentTypeFilter.value))
const hasShadowFilters = computed(() => Boolean(shadowChannelFilter.value || shadowActionFilter.value || shadowLimitFilter.value !== '100'))
const hasToolFilters = computed(() => Boolean(
  toolStatusFilter.value ||
  toolNameFilter.value ||
  toolProviderFilter.value ||
  toolDecisionFilter.value ||
  toolRiskFilter.value ||
  toolRequiresApprovalFilter.value ||
  toolLimitFilter.value !== '100',
))
const isLoginPath = computed(() => currentPath.value === '/login')
const hasAccess = computed(() => !REQUIRE_LOGIN || Boolean(adminApiKey.value))
const isDashboardPath = computed(() => currentPath.value === '/dashboard' || currentPath.value === '/')
const isCalendarPath = computed(() => currentPath.value === '/calendar')
const isDocumentListPath = computed(() => currentPath.value === '/documents')
const isShadowDecisionListPath = computed(() => currentPath.value === '/audit/shadow-decisions')
const isToolExecutionListPath = computed(() => currentPath.value === '/tools/executions')
const isReviewListPath = computed(() => currentPath.value === '/human-review')
const isTechnicianListPath = computed(() => currentPath.value === '/technicians')
const isVisitListPath = computed(() => currentPath.value === '/visits')
const isIncidentListPath = computed(() => currentPath.value === '/incidents')
const selectedIncidentId = computed(() => {
  const match = currentPath.value.match(/^\/incidents\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedReviewItemId = computed(() => {
  const match = currentPath.value.match(/^\/human-review\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedTechnicianId = computed(() => {
  const match = currentPath.value.match(/^\/technicians\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedVisitId = computed(() => {
  const match = currentPath.value.match(/^\/visits\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedDocumentId = computed(() => {
  const match = currentPath.value.match(/^\/documents\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedShadowDecisionId = computed(() => {
  const match = currentPath.value.match(/^\/audit\/shadow-decisions\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedToolExecutionId = computed(() => {
  const match = currentPath.value.match(/^\/tools\/executions\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})

async function loadDashboardSummary(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    dashboardSummary.value = await fetchDashboardSummary()
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar el dashboard'
    dashboardSummary.value = null
  } finally {
    loading.value = false
  }
}

async function loadIncidents(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    incidents.value = await fetchIncidents({
      status: statusFilter.value || undefined,
      priority: priorityFilter.value || undefined,
      limit: 100,
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar las incidencias'
    incidents.value = []
  } finally {
    loading.value = false
  }
}

async function loadHumanReviewItems(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    reviewItems.value = await fetchHumanReviewItems({
      status: reviewStatusFilter.value || undefined,
      priority: reviewPriorityFilter.value || undefined,
      limit: 100,
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar la cola de revisión'
    reviewItems.value = []
  } finally {
    loading.value = false
  }
}

async function loadTechnicians(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    technicians.value = await fetchTechnicians({
      active: technicianActiveFilter.value === '' ? undefined : technicianActiveFilter.value === 'true',
      limit: 100,
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar los técnicos'
    technicians.value = []
  } finally {
    loading.value = false
  }
}

async function loadVisits(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    const [loadedVisits, loadedTechnicians] = await Promise.all([
      fetchVisits({
        technician_id: visitTechnicianFilter.value || undefined,
        status: visitStatusFilter.value || undefined,
        limit: 100,
      }),
      fetchTechnicians({ active: true, limit: 200 }),
    ])
    visits.value = loadedVisits
    technicians.value = loadedTechnicians
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar las visitas'
    visits.value = []
  } finally {
    loading.value = false
  }
}

async function loadDocuments(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    documents.value = await fetchDocuments({
      document_type: documentTypeFilter.value || undefined,
      status: documentStatusFilter.value || undefined,
      limit: 100,
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar los documentos'
    documents.value = []
  } finally {
    loading.value = false
  }
}

async function loadShadowDecisionRecords(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    shadowDecisionRecords.value = await listShadowDecisionRecords({
      channel: shadowChannelFilter.value || undefined,
      shadow_action_type: shadowActionFilter.value || undefined,
      limit: Number(shadowLimitFilter.value || '100'),
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar las evaluaciones IA'
    shadowDecisionRecords.value = []
  } finally {
    loading.value = false
  }
}

async function loadToolExecutionRecords(): Promise<void> {
  if (!hasAccess.value) return

  loading.value = true
  error.value = null

  try {
    toolExecutionRecords.value = await fetchToolExecutionRecords({
      status: toolStatusFilter.value || undefined,
      tool_name: toolNameFilter.value || undefined,
      provider: toolProviderFilter.value || undefined,
      decision: toolDecisionFilter.value || undefined,
      risk_level: toolRiskFilter.value === '' ? undefined : Number(toolRiskFilter.value),
      requires_approval: toolRequiresApprovalFilter.value === ''
        ? undefined
        : toolRequiresApprovalFilter.value === 'true',
      limit: Number(toolLimitFilter.value || '100'),
    })
  } catch (err) {
    if (isUnauthorizedError(err)) {
      handleUnauthorized()
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar las acciones IA'
    toolExecutionRecords.value = []
  } finally {
    loading.value = false
  }
}

function clearFilters(): void {
  statusFilter.value = ''
  priorityFilter.value = ''
  void loadIncidents()
}

function clearReviewFilters(): void {
  reviewStatusFilter.value = ''
  reviewPriorityFilter.value = ''
  void loadHumanReviewItems()
}

function clearTechnicianFilters(): void {
  technicianActiveFilter.value = ''
  void loadTechnicians()
}

function clearVisitFilters(): void {
  visitStatusFilter.value = ''
  visitTechnicianFilter.value = ''
  void loadVisits()
}

function clearDocumentFilters(): void {
  documentTypeFilter.value = ''
  documentStatusFilter.value = ''
  void loadDocuments()
}

function clearShadowFilters(): void {
  shadowChannelFilter.value = ''
  shadowActionFilter.value = ''
  shadowLimitFilter.value = '100'
  void loadShadowDecisionRecords()
}

function clearToolFilters(): void {
  toolStatusFilter.value = ''
  toolNameFilter.value = ''
  toolProviderFilter.value = ''
  toolDecisionFilter.value = ''
  toolRiskFilter.value = ''
  toolRequiresApprovalFilter.value = ''
  toolLimitFilter.value = '100'
  void loadToolExecutionRecords()
}

function syncPath(): void {
  currentPath.value = window.location.pathname
  enforceRouteProtection()
  if (!hasAccess.value) return
  if (isDashboardPath.value) void loadDashboardSummary()
  if (isIncidentListPath.value) void loadIncidents()
  if (isReviewListPath.value) void loadHumanReviewItems()
  if (isTechnicianListPath.value) void loadTechnicians()
  if (isVisitListPath.value) void loadVisits()
  if (isDocumentListPath.value) void loadDocuments()
  if (isShadowDecisionListPath.value) void loadShadowDecisionRecords()
  if (isToolExecutionListPath.value) void loadToolExecutionRecords()
}

function navigate(path: string): void {
  window.history.pushState({}, '', path)
  syncPath()
}

function openIncident(incidentId: string): void {
  navigate(`/incidents/${encodeURIComponent(incidentId)}`)
}

function openDashboard(): void {
  navigate('/dashboard')
  void loadDashboardSummary()
}

function openIncidentList(): void {
  navigate('/incidents')
  void loadIncidents()
}

function openHumanReview(itemId: string): void {
  navigate(`/human-review/${encodeURIComponent(itemId)}`)
}

function openHumanReviewList(): void {
  navigate('/human-review')
  void loadHumanReviewItems()
}

function openTechnician(technicianId: string): void {
  navigate(`/technicians/${encodeURIComponent(technicianId)}`)
}

function openNewTechnician(): void {
  navigate('/technicians/new')
}

function openTechnicianList(): void {
  navigate('/technicians')
  void loadTechnicians()
}

function openVisit(visitId: string): void {
  navigate(`/visits/${encodeURIComponent(visitId)}`)
}

function openNewVisit(): void {
  navigate('/visits/new')
}

function openVisitList(): void {
  navigate('/visits')
  void loadVisits()
}

function openCalendar(): void {
  navigate('/calendar')
}

function openDocument(documentId: string): void {
  navigate(`/documents/${encodeURIComponent(documentId)}`)
}

function openDocumentList(): void {
  navigate('/documents')
  void loadDocuments()
}

function openShadowDecision(recordId: string): void {
  navigate(`/audit/shadow-decisions/${encodeURIComponent(recordId)}`)
}

function openShadowDecisionList(): void {
  navigate('/audit/shadow-decisions')
  void loadShadowDecisionRecords()
}

function openToolExecution(recordId: string): void {
  navigate(`/tools/executions/${encodeURIComponent(recordId)}`)
}

function openToolExecutionList(): void {
  navigate('/tools/executions')
  void loadToolExecutionRecords()
}

function handleTechnicianCreated(technicianId: string): void {
  window.history.replaceState({}, '', `/technicians/${encodeURIComponent(technicianId)}`)
  currentPath.value = window.location.pathname
}

function handleVisitCreated(visitId: string): void {
  window.history.replaceState({}, '', `/visits/${encodeURIComponent(visitId)}`)
  currentPath.value = window.location.pathname
}

async function handleLogin(payload: LoginPayload): Promise<void> {
  try {
    const authIndicator = await loginWithCredentials(payload)
    if (AUTH_MODE === 'api_key' && payload.apiKey) {
      setStoredAdminApiKey(payload.apiKey)
    }
    adminApiKey.value = authIndicator
    authMessage.value = null
    navigate('/dashboard')
    void loadDashboardSummary()
  } catch (err) {
    authMessage.value = err instanceof Error ? err.message : 'No se pudo iniciar sesión'
  }
}

function handleLogout(): void {
  void logoutCurrentUser()
  adminApiKey.value = ''
  dashboardSummary.value = null
  incidents.value = []
  reviewItems.value = []
  technicians.value = []
  visits.value = []
  documents.value = []
  shadowDecisionRecords.value = []
  toolExecutionRecords.value = []
  authMessage.value = null
  navigate('/login')
}

function handleUnauthorized(): void {
  void logoutCurrentUser()
  adminApiKey.value = ''
  dashboardSummary.value = null
  incidents.value = []
  reviewItems.value = []
  technicians.value = []
  visits.value = []
  documents.value = []
  shadowDecisionRecords.value = []
  toolExecutionRecords.value = []
  authMessage.value = 'No autorizado. Revisa las credenciales e inténtalo de nuevo.'
  navigate('/login')
}

function enforceRouteProtection(): void {
  if (!REQUIRE_LOGIN) return

  if (!adminApiKey.value && !isLoginPath.value) {
    window.history.replaceState({}, '', '/login')
    currentPath.value = window.location.pathname
    return
  }

  if (adminApiKey.value && isLoginPath.value) {
    window.history.replaceState({}, '', '/dashboard')
    currentPath.value = window.location.pathname
  }
}

onMounted(() => {
  window.addEventListener('popstate', syncPath)
  stopAuthObserver = observeAuthState((hasAuthAccess) => {
    if (AUTH_MODE !== 'firebase') return
    adminApiKey.value = hasAuthAccess ? getStoredAuthIndicator() : ''
    enforceRouteProtection()
  })
  enforceRouteProtection()
  if (hasAccess.value && isDashboardPath.value) {
    void loadDashboardSummary()
    return
  }
  if (hasAccess.value && isCalendarPath.value) {
    return
  }
  if (hasAccess.value && isReviewListPath.value) {
    void loadHumanReviewItems()
    return
  }
  if (hasAccess.value && isTechnicianListPath.value) {
    void loadTechnicians()
    return
  }
  if (hasAccess.value && isVisitListPath.value) {
    void loadVisits()
    return
  }
  if (hasAccess.value && isDocumentListPath.value) {
    void loadDocuments()
    return
  }
  if (hasAccess.value && isShadowDecisionListPath.value) {
    void loadShadowDecisionRecords()
    return
  }
  if (hasAccess.value && isToolExecutionListPath.value) {
    void loadToolExecutionRecords()
    return
  }
  if (hasAccess.value && isIncidentListPath.value) {
    void loadIncidents()
  }
})

onUnmounted(() => {
  window.removeEventListener('popstate', syncPath)
  if (stopAuthObserver) stopAuthObserver()
})
</script>

<template>
  <LoginPanel
    v-if="REQUIRE_LOGIN && isLoginPath"
    :auth-mode="AUTH_MODE"
    :message="authMessage"
    @login="handleLogin"
  />

  <main v-else class="appShell">
    <IncidentDetail
      v-if="selectedIncidentId"
      :incident-id="selectedIncidentId"
      @back="openIncidentList"
      @unauthorized="handleUnauthorized"
    />

    <HumanReviewDetail
      v-else-if="selectedReviewItemId"
      :item-id="selectedReviewItemId"
      @back="openHumanReviewList"
      @unauthorized="handleUnauthorized"
    />

    <TechnicianDetail
      v-else-if="selectedTechnicianId"
      :technician-id="selectedTechnicianId"
      @back="openTechnicianList"
      @created="handleTechnicianCreated"
      @unauthorized="handleUnauthorized"
    />

    <VisitDetail
      v-else-if="selectedVisitId"
      :visit-id="selectedVisitId"
      @back="openVisitList"
      @created="handleVisitCreated"
      @unauthorized="handleUnauthorized"
    />

    <DocumentDetail
      v-else-if="selectedDocumentId"
      :document-id="selectedDocumentId"
      @back="openDocumentList"
      @unauthorized="handleUnauthorized"
    />

    <ShadowDecisionDetail
      v-else-if="selectedShadowDecisionId"
      :record-id="selectedShadowDecisionId"
      @back="openShadowDecisionList"
      @unauthorized="handleUnauthorized"
    />

    <ToolExecutionDetail
      v-else-if="selectedToolExecutionId"
      :execution-id="selectedToolExecutionId"
      @back="openToolExecutionList"
      @unauthorized="handleUnauthorized"
    />

    <template v-else-if="isDashboardPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Panel operativo</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="primaryButton" type="button" disabled>Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
            </button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">
              Técnicos
            </button>
            <button class="secondaryButton" type="button" @click="openVisitList">
              Visitas
            </button>
            <button class="secondaryButton" type="button" @click="openCalendar">
              Calendario
            </button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadDashboardSummary">
            Actualizar
          </button>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <DashboardPanel
        :summary="dashboardSummary"
        :loading="loading"
        :error="error"
        @refresh="loadDashboardSummary"
        @open="navigate"
      />
    </template>

    <template v-else-if="isCalendarPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Calendario</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
            </button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">
              Técnicos
            </button>
            <button class="secondaryButton" type="button" @click="openVisitList">
              Visitas
            </button>
            <button class="primaryButton" type="button" disabled>Calendario</button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <CalendarPanel
        @open="openVisit"
        @unauthorized="handleUnauthorized"
      />
    </template>

    <template v-else-if="isDocumentListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Documentos</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">Revisión humana</button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">Técnicos</button>
            <button class="secondaryButton" type="button" @click="openVisitList">Visitas</button>
            <button class="secondaryButton" type="button" @click="openCalendar">Calendario</button>
            <button class="primaryButton" type="button" disabled>Documentos</button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">Evaluación IA</button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">Acciones IA</button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadDocuments">
            Actualizar
          </button>
          <button v-if="REQUIRE_LOGIN" class="secondaryButton" type="button" @click="handleLogout">
            Salir
          </button>
        </div>
      </header>

      <section class="filters" aria-label="Filtros de documentos">
        <label>
          Tipo
          <select v-model="documentTypeFilter" @change="loadDocuments">
            <option value="">Todos</option>
            <option v-for="type in DOCUMENT_TYPE_OPTIONS" :key="type" :value="type">
              {{ formatDocumentType(type) }}
            </option>
          </select>
        </label>

        <label>
          Estado
          <select v-model="documentStatusFilter" @change="loadDocuments">
            <option value="">Todos</option>
            <option value="draft">{{ formatStatus('draft') }}</option>
            <option value="reviewed">{{ formatStatus('reviewed') }}</option>
            <option value="archived">{{ formatStatus('archived') }}</option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasDocumentFilters" @click="clearDocumentFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando documentos...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="documents.length === 0" class="stateMessage">
          No hay documentos para los filtros seleccionados.
        </div>
        <DocumentTable v-else :documents="documents" @open="openDocument" />
      </section>
    </template>

    <template v-else-if="isShadowDecisionListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Evaluación IA</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">Revisión humana</button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">Técnicos</button>
            <button class="secondaryButton" type="button" @click="openVisitList">Visitas</button>
            <button class="secondaryButton" type="button" @click="openCalendar">Calendario</button>
            <button class="secondaryButton" type="button" @click="openDocumentList">Documentos</button>
            <button class="primaryButton" type="button" disabled>Evaluación IA</button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">Acciones IA</button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadShadowDecisionRecords">
            Actualizar
          </button>
          <button v-if="REQUIRE_LOGIN" class="secondaryButton" type="button" @click="handleLogout">
            Salir
          </button>
        </div>
      </header>

      <section class="contentBand">
        <div class="infoPanel" aria-label="Explicación de evaluación IA">
          Esta pantalla compara la decisión del sistema actual con la decisión que habría tomado la IA real.
          El sistema actual sigue respondiendo al cliente. La IA solo observa en modo sombra y no ejecuta acciones reales.
        </div>
      </section>

      <section class="filters" aria-label="Filtros de evaluación IA">
        <label>
          Canal
          <select v-model="shadowChannelFilter" @change="loadShadowDecisionRecords">
            <option value="">Todos</option>
            <option value="telegram">{{ formatChannel('telegram') }}</option>
            <option value="whatsapp">{{ formatChannel('whatsapp') }}</option>
            <option value="webchat">{{ formatChannel('webchat') }}</option>
            <option value="email">{{ formatChannel('email') }}</option>
            <option value="sms">{{ formatChannel('sms') }}</option>
          </select>
        </label>

        <label>
          Decisión de la IA
          <select v-model="shadowActionFilter" @change="loadShadowDecisionRecords">
            <option value="">Todas</option>
            <option v-for="action in SHADOW_ACTION_TYPES" :key="action" :value="action">
              {{ formatAction(action) }}
            </option>
          </select>
        </label>

        <label>
          Límite
          <select v-model="shadowLimitFilter" @change="loadShadowDecisionRecords">
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasShadowFilters" @click="clearShadowFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando evaluaciones IA...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="shadowDecisionRecords.length === 0" class="stateMessage">
          No hay evaluaciones IA para los filtros seleccionados.
        </div>
        <ShadowDecisionTable
          v-else
          :records="shadowDecisionRecords"
          @open="openShadowDecision"
        />
      </section>
    </template>

    <template v-else-if="isToolExecutionListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Acciones IA</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">Revisión humana</button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">Técnicos</button>
            <button class="secondaryButton" type="button" @click="openVisitList">Visitas</button>
            <button class="secondaryButton" type="button" @click="openCalendar">Calendario</button>
            <button class="secondaryButton" type="button" @click="openDocumentList">Documentos</button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">Evaluación IA</button>
            <button class="primaryButton" type="button" disabled>Acciones IA</button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadToolExecutionRecords">
            Actualizar
          </button>
          <button v-if="REQUIRE_LOGIN" class="secondaryButton" type="button" @click="handleLogout">
            Salir
          </button>
        </div>
      </header>

      <section class="contentBand">
        <div class="infoPanel" aria-label="Explicación de acciones IA">
          Esta pantalla muestra propuestas de herramientas hechas por el agente. Se pueden revisar y aprobar,
          pero en esta fase ninguna aprobación ejecuta Gmail, Calendar, Telegram, WhatsApp ni Firestore.
        </div>
      </section>

      <section class="filters" aria-label="Filtros de acciones IA">
        <label>
          Estado revisión
          <select v-model="toolStatusFilter" @change="loadToolExecutionRecords">
            <option value="">Todos</option>
            <option v-for="status in TOOL_REVIEW_STATUSES" :key="status" :value="status">
              {{ formatReviewStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Herramienta
          <select v-model="toolNameFilter" @change="loadToolExecutionRecords">
            <option value="">Todas</option>
            <option value="incident.propose_incident">{{ formatToolName('incident.propose_incident') }}</option>
            <option value="calendar.propose_event">{{ formatToolName('calendar.propose_event') }}</option>
            <option value="gmail.create_draft">{{ formatToolName('gmail.create_draft') }}</option>
            <option value="telegram.draft_message">{{ formatToolName('telegram.draft_message') }}</option>
            <option value="whatsapp.draft_message">{{ formatToolName('whatsapp.draft_message') }}</option>
          </select>
        </label>

        <label>
          Proveedor
          <select v-model="toolProviderFilter" @change="loadToolExecutionRecords">
            <option value="">Todos</option>
            <option value="incident_service">{{ formatToolProvider('incident_service') }}</option>
            <option value="calendar">{{ formatToolProvider('calendar') }}</option>
            <option value="gmail">{{ formatToolProvider('gmail') }}</option>
            <option value="telegram">{{ formatToolProvider('telegram') }}</option>
            <option value="whatsapp">{{ formatToolProvider('whatsapp') }}</option>
          </select>
        </label>

        <label>
          Decisión
          <select v-model="toolDecisionFilter" @change="loadToolExecutionRecords">
            <option value="">Todas</option>
            <option value="allow">{{ formatToolDecision('allow') }}</option>
            <option value="deny">{{ formatToolDecision('deny') }}</option>
            <option value="require_human_approval">{{ formatToolDecision('require_human_approval') }}</option>
            <option value="convert_to_draft">{{ formatToolDecision('convert_to_draft') }}</option>
            <option value="require_more_data">{{ formatToolDecision('require_more_data') }}</option>
          </select>
        </label>

        <label>
          Riesgo
          <select v-model="toolRiskFilter" @change="loadToolExecutionRecords">
            <option value="">Todos</option>
            <option v-for="risk in [0, 1, 2, 3, 4, 5]" :key="risk" :value="String(risk)">
              {{ formatRiskLevel(risk) }}
            </option>
          </select>
        </label>

        <label>
          Aprobación
          <select v-model="toolRequiresApprovalFilter" @change="loadToolExecutionRecords">
            <option value="">Todas</option>
            <option value="true">Requiere aprobación</option>
            <option value="false">No requiere aprobación</option>
          </select>
        </label>

        <label>
          Límite
          <select v-model="toolLimitFilter" @change="loadToolExecutionRecords">
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasToolFilters" @click="clearToolFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando acciones IA...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="toolExecutionRecords.length === 0" class="stateMessage">
          No hay acciones IA para los filtros seleccionados.
        </div>
        <ToolExecutionTable
          v-else
          :records="toolExecutionRecords"
          @open="openToolExecution"
        />
      </section>
    </template>

    <template v-else-if="isReviewListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Revisión humana</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="primaryButton" type="button" disabled>Revisión humana</button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">
              Técnicos
            </button>
            <button class="secondaryButton" type="button" @click="openVisitList">
              Visitas
            </button>
            <button class="secondaryButton" type="button" @click="openCalendar">
              Calendario
            </button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadHumanReviewItems">
            Actualizar
          </button>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <section class="filters" aria-label="Filtros de revisión humana">
        <label>
          Estado
          <select v-model="reviewStatusFilter" @change="loadHumanReviewItems">
            <option value="">Todos</option>
            <option v-for="status in HUMAN_REVIEW_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="reviewPriorityFilter" @change="loadHumanReviewItems">
            <option value="">Todas</option>
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ formatPriority(priority) }}
            </option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasReviewFilters" @click="clearReviewFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando revisión humana...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="reviewItems.length === 0" class="stateMessage">
          No hay elementos de revisión para los filtros seleccionados.
        </div>
        <HumanReviewTable v-else :items="reviewItems" @open="openHumanReview" />
      </section>
    </template>

    <template v-else-if="isTechnicianListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Técnicos</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
            </button>
            <button class="primaryButton" type="button" disabled>Técnicos</button>
            <button class="secondaryButton" type="button" @click="openVisitList">
              Visitas
            </button>
            <button class="secondaryButton" type="button" @click="openCalendar">
              Calendario
            </button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button class="primaryButton" type="button" @click="openNewTechnician">
            Nuevo técnico
          </button>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadTechnicians">
            Actualizar
          </button>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <section class="filters" aria-label="Filtros de técnicos">
        <label>
          Activo
          <select v-model="technicianActiveFilter" @change="loadTechnicians">
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasTechnicianFilters" @click="clearTechnicianFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando técnicos...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="technicians.length === 0" class="stateMessage">
          No hay técnicos para los filtros seleccionados.
        </div>
        <TechnicianTable v-else :technicians="technicians" @open="openTechnician" />
      </section>
    </template>

    <template v-else-if="isVisitListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Visitas</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
            </button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">
              Técnicos
            </button>
            <button class="primaryButton" type="button" disabled>Visitas</button>
            <button class="secondaryButton" type="button" @click="openCalendar">
              Calendario
            </button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button class="primaryButton" type="button" @click="openNewVisit">
            Nueva visita
          </button>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadVisits">
            Actualizar
          </button>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <section class="filters" aria-label="Filtros de visitas">
        <label>
          Estado
          <select v-model="visitStatusFilter" @change="loadVisits">
            <option value="">Todos</option>
            <option v-for="status in VISIT_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Técnico
          <select v-model="visitTechnicianFilter" @change="loadVisits">
            <option value="">Todos</option>
            <option v-for="technician in technicians" :key="technician.id" :value="technician.id">
              {{ technician.name }}
            </option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasVisitFilters" @click="clearVisitFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando visitas...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="visits.length === 0" class="stateMessage">
          No hay visitas para los filtros seleccionados.
        </div>
        <VisitTable v-else :visits="visits" @open="openVisit" />
      </section>
    </template>

    <template v-else>
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Incidencias</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">Panel</button>
            <button class="primaryButton" type="button" disabled>Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
            </button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">
              Técnicos
            </button>
            <button class="secondaryButton" type="button" @click="openVisitList">
              Visitas
            </button>
            <button class="secondaryButton" type="button" @click="openCalendar">
              Calendario
            </button>
            <button class="secondaryButton" type="button" @click="openDocumentList">
              Documentos
            </button>
            <button class="secondaryButton" type="button" @click="openShadowDecisionList">
              Evaluación IA
            </button>
            <button class="secondaryButton" type="button" @click="openToolExecutionList">
              Acciones IA
            </button>
          </nav>
          <button class="primaryButton" type="button" :disabled="loading" @click="loadIncidents">
            Actualizar
          </button>
          <button
            v-if="REQUIRE_LOGIN"
            class="secondaryButton"
            type="button"
            @click="handleLogout"
          >
            Salir
          </button>
        </div>
      </header>

      <section class="filters" aria-label="Filtros de incidencias">
        <label>
          Estado
          <select v-model="statusFilter" @change="loadIncidents">
            <option value="">Todos</option>
            <option v-for="status in INCIDENT_STATUSES" :key="status" :value="status">
              {{ formatStatus(status) }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="priorityFilter" @change="loadIncidents">
            <option value="">Todas</option>
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ formatPriority(priority) }}
            </option>
          </select>
        </label>

        <button class="secondaryButton" type="button" :disabled="!hasFilters" @click="clearFilters">
          Limpiar
        </button>
      </section>

      <section class="contentBand">
        <div v-if="loading" class="stateMessage">Cargando incidencias...</div>
        <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>
        <div v-else-if="incidents.length === 0" class="stateMessage">
          No hay incidencias para los filtros seleccionados.
        </div>
        <IncidentTable v-else :incidents="incidents" @open="openIncident" />
      </section>
    </template>
  </main>
</template>
