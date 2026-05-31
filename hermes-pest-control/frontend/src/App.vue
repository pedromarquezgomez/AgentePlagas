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
import TechnicianDetail from './components/TechnicianDetail.vue'
import TechnicianTable from './components/TechnicianTable.vue'
import VisitDetail from './components/VisitDetail.vue'
import VisitTable from './components/VisitTable.vue'
import {
  clearStoredAdminApiKey,
  fetchDashboardSummary,
  fetchDocuments,
  fetchHumanReviewItems,
  fetchIncidents,
  fetchTechnicians,
  fetchVisits,
  getStoredAdminApiKey,
  HUMAN_REVIEW_STATUSES,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  isUnauthorizedError,
  REQUIRE_LOGIN,
  setStoredAdminApiKey,
  type DashboardSummary,
  type OperationalDocument,
  type HumanReviewItem,
  type Incident,
  type Technician,
  type Visit,
  VISIT_STATUSES,
} from './services/api'

const incidents = ref<Incident[]>([])
const dashboardSummary = ref<DashboardSummary | null>(null)
const reviewItems = ref<HumanReviewItem[]>([])
const technicians = ref<Technician[]>([])
const visits = ref<Visit[]>([])
const documents = ref<OperationalDocument[]>([])
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
const currentPath = ref(window.location.pathname)
const adminApiKey = ref(getStoredAdminApiKey())
const authMessage = ref<string | null>(null)

const hasFilters = computed(() => Boolean(statusFilter.value || priorityFilter.value))
const hasReviewFilters = computed(() => Boolean(reviewStatusFilter.value || reviewPriorityFilter.value))
const hasTechnicianFilters = computed(() => Boolean(technicianActiveFilter.value))
const hasVisitFilters = computed(() => Boolean(visitStatusFilter.value || visitTechnicianFilter.value))
const hasDocumentFilters = computed(() => Boolean(documentStatusFilter.value || documentTypeFilter.value))
const isLoginPath = computed(() => currentPath.value === '/login')
const hasAccess = computed(() => !REQUIRE_LOGIN || Boolean(adminApiKey.value))
const isDashboardPath = computed(() => currentPath.value === '/dashboard' || currentPath.value === '/')
const isCalendarPath = computed(() => currentPath.value === '/calendar')
const isDocumentListPath = computed(() => currentPath.value === '/documents')
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

function handleTechnicianCreated(technicianId: string): void {
  window.history.replaceState({}, '', `/technicians/${encodeURIComponent(technicianId)}`)
  currentPath.value = window.location.pathname
}

function handleVisitCreated(visitId: string): void {
  window.history.replaceState({}, '', `/visits/${encodeURIComponent(visitId)}`)
  currentPath.value = window.location.pathname
}

function handleLogin(apiKey: string): void {
  setStoredAdminApiKey(apiKey)
  adminApiKey.value = apiKey
  authMessage.value = null
  navigate('/dashboard')
  void loadDashboardSummary()
}

function handleLogout(): void {
  clearStoredAdminApiKey()
  adminApiKey.value = ''
  dashboardSummary.value = null
  incidents.value = []
  reviewItems.value = []
  technicians.value = []
  visits.value = []
  documents.value = []
  authMessage.value = null
  navigate('/login')
}

function handleUnauthorized(): void {
  clearStoredAdminApiKey()
  adminApiKey.value = ''
  dashboardSummary.value = null
  incidents.value = []
  reviewItems.value = []
  technicians.value = []
  visits.value = []
  documents.value = []
  authMessage.value = 'No autorizado. Revisa la API key e inténtalo de nuevo.'
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
  if (hasAccess.value && isIncidentListPath.value) {
    void loadIncidents()
  }
})

onUnmounted(() => {
  window.removeEventListener('popstate', syncPath)
})
</script>

<template>
  <LoginPanel
    v-if="REQUIRE_LOGIN && isLoginPath"
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

    <template v-else-if="isDashboardPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Dashboard</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="primaryButton" type="button" disabled>Dashboard</button>
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
            <button class="secondaryButton" type="button" @click="openDashboard">
              Dashboard
            </button>
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
            <button class="secondaryButton" type="button" @click="openDashboard">Dashboard</button>
            <button class="secondaryButton" type="button" @click="openIncidentList">Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">Revisión humana</button>
            <button class="secondaryButton" type="button" @click="openTechnicianList">Técnicos</button>
            <button class="secondaryButton" type="button" @click="openVisitList">Visitas</button>
            <button class="secondaryButton" type="button" @click="openCalendar">Calendario</button>
            <button class="primaryButton" type="button" disabled>Documentos</button>
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
            <option value="incident_summary">incident_summary</option>
            <option value="technician_brief">technician_brief</option>
            <option value="post_treatment_recommendations">post_treatment_recommendations</option>
            <option value="work_report_draft">work_report_draft</option>
          </select>
        </label>

        <label>
          Estado
          <select v-model="documentStatusFilter" @change="loadDocuments">
            <option value="">Todos</option>
            <option value="draft">draft</option>
            <option value="reviewed">reviewed</option>
            <option value="archived">archived</option>
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

    <template v-else-if="isReviewListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Revisión humana</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openDashboard">
              Dashboard
            </button>
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
              {{ status }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="reviewPriorityFilter" @change="loadHumanReviewItems">
            <option value="">Todas</option>
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ priority }}
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
            <button class="secondaryButton" type="button" @click="openDashboard">
              Dashboard
            </button>
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
            <button class="secondaryButton" type="button" @click="openDashboard">
              Dashboard
            </button>
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
              {{ status }}
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
            <button class="secondaryButton" type="button" @click="openDashboard">
              Dashboard
            </button>
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
              {{ status }}
            </option>
          </select>
        </label>

        <label>
          Prioridad
          <select v-model="priorityFilter" @change="loadIncidents">
            <option value="">Todas</option>
            <option v-for="priority in INCIDENT_PRIORITIES" :key="priority" :value="priority">
              {{ priority }}
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
