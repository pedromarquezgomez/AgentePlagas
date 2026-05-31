<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import HumanReviewDetail from './components/HumanReviewDetail.vue'
import HumanReviewTable from './components/HumanReviewTable.vue'
import IncidentDetail from './components/IncidentDetail.vue'
import IncidentTable from './components/IncidentTable.vue'
import LoginPanel from './components/LoginPanel.vue'
import {
  clearStoredAdminApiKey,
  fetchHumanReviewItems,
  fetchIncidents,
  getStoredAdminApiKey,
  HUMAN_REVIEW_STATUSES,
  INCIDENT_PRIORITIES,
  INCIDENT_STATUSES,
  isUnauthorizedError,
  REQUIRE_LOGIN,
  setStoredAdminApiKey,
  type HumanReviewItem,
  type Incident,
} from './services/api'

const incidents = ref<Incident[]>([])
const reviewItems = ref<HumanReviewItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref('')
const priorityFilter = ref('')
const reviewStatusFilter = ref('')
const reviewPriorityFilter = ref('')
const currentPath = ref(window.location.pathname)
const adminApiKey = ref(getStoredAdminApiKey())
const authMessage = ref<string | null>(null)

const hasFilters = computed(() => Boolean(statusFilter.value || priorityFilter.value))
const hasReviewFilters = computed(() => Boolean(reviewStatusFilter.value || reviewPriorityFilter.value))
const isLoginPath = computed(() => currentPath.value === '/login')
const hasAccess = computed(() => !REQUIRE_LOGIN || Boolean(adminApiKey.value))
const isReviewListPath = computed(() => currentPath.value === '/human-review')
const isIncidentListPath = computed(() => currentPath.value === '/incidents' || currentPath.value === '/')
const selectedIncidentId = computed(() => {
  const match = currentPath.value.match(/^\/incidents\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})
const selectedReviewItemId = computed(() => {
  const match = currentPath.value.match(/^\/human-review\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
})

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

function syncPath(): void {
  currentPath.value = window.location.pathname
  enforceRouteProtection()
}

function navigate(path: string): void {
  window.history.pushState({}, '', path)
  syncPath()
}

function openIncident(incidentId: string): void {
  navigate(`/incidents/${encodeURIComponent(incidentId)}`)
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

function handleLogin(apiKey: string): void {
  setStoredAdminApiKey(apiKey)
  adminApiKey.value = apiKey
  authMessage.value = null
  navigate('/incidents')
  void loadIncidents()
}

function handleLogout(): void {
  clearStoredAdminApiKey()
  adminApiKey.value = ''
  incidents.value = []
  reviewItems.value = []
  authMessage.value = null
  navigate('/login')
}

function handleUnauthorized(): void {
  clearStoredAdminApiKey()
  adminApiKey.value = ''
  incidents.value = []
  reviewItems.value = []
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
    window.history.replaceState({}, '', '/incidents')
    currentPath.value = window.location.pathname
  }
}

onMounted(() => {
  window.addEventListener('popstate', syncPath)
  enforceRouteProtection()
  if (hasAccess.value && isReviewListPath.value) {
    void loadHumanReviewItems()
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

    <template v-else-if="isReviewListPath">
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Revisión humana</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="secondaryButton" type="button" @click="openIncidentList">
              Incidencias
            </button>
            <button class="primaryButton" type="button" disabled>Revisión humana</button>
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

    <template v-else>
      <header class="topBar">
        <div>
          <p class="eyebrow">Hermes Pest Control</p>
          <h1>Incidencias</h1>
        </div>
        <div class="topActions">
          <nav class="sectionNav" aria-label="Navegación del panel">
            <button class="primaryButton" type="button" disabled>Incidencias</button>
            <button class="secondaryButton" type="button" @click="openHumanReviewList">
              Revisión humana
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
