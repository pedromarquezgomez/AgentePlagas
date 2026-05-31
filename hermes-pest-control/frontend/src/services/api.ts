export const INCIDENT_STATUSES = [
  'new',
  'pending_review',
  'waiting_for_client_data',
  'ready_for_scheduling',
  'scheduled',
  'in_progress',
  'completed',
  'follow_up_pending',
  'closed',
  'cancelled',
] as const

export const INCIDENT_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const
export const HUMAN_REVIEW_STATUSES = ['open', 'in_review', 'resolved', 'dismissed'] as const
export const VISIT_STATUSES = ['draft', 'scheduled', 'in_progress', 'completed', 'cancelled'] as const

export type IncidentStatus = (typeof INCIDENT_STATUSES)[number]
export type IncidentPriority = (typeof INCIDENT_PRIORITIES)[number]
export type HumanReviewStatus = (typeof HUMAN_REVIEW_STATUSES)[number]
export type VisitStatus = (typeof VISIT_STATUSES)[number]

export interface Incident {
  id: string
  conversation_id: string | null
  channel: string
  pest_type: string | null
  location: string | null
  affected_area: string | null
  priority: IncidentPriority | string
  status: IncidentStatus | string
  summary: string | null
  internal_notes?: string | null
  created_at?: string
  updated_at?: string
}

export interface IncidentFilters {
  status?: string
  priority?: string
  limit?: number
}

export interface IncidentUpdate {
  status?: IncidentStatus
  priority?: IncidentPriority
  internal_notes?: string | null
}

export interface DecisionRecord {
  id: string
  trace_id: string
  conversation_id: string
  message_id?: string | null
  incident_id?: string | null
  channel: string
  hermes_mode: string
  action_type: string
  incident_should_create: boolean
  pest_type?: string | null
  priority?: string | null
  fallback_used: boolean
  fallback_reason?: string | null
  prompt_version: string
  skill_version: string
  response_contract_version: string
  created_at?: string
}

export interface DecisionRecordFilters {
  conversation_id?: string
  action_type?: string
  fallback_used?: boolean
  limit?: number
}

export interface HumanReviewItem {
  id: string
  trace_id: string
  conversation_id: string
  incident_id?: string | null
  decision_record_id?: string | null
  channel: string
  reason: string
  priority: IncidentPriority | string
  status: HumanReviewStatus | string
  summary?: string | null
  created_at?: string
  updated_at?: string
  resolved_at?: string | null
  assigned_to?: string | null
  resolution_notes?: string | null
  metadata?: Record<string, unknown>
}

export interface HumanReviewFilters {
  status?: string
  priority?: string
  limit?: number
}

export interface HumanReviewUpdate {
  status?: HumanReviewStatus
  assigned_to?: string | null
  resolution_notes?: string | null
}

export interface Technician {
  id: string
  name: string
  phone?: string | null
  email?: string | null
  active: boolean
  service_area?: string | null
  skills: string[]
  created_at?: string
  updated_at?: string
}

export interface TechnicianFilters {
  active?: boolean
  limit?: number
}

export interface TechnicianCreate {
  name: string
  phone?: string | null
  email?: string | null
  active?: boolean
  service_area?: string | null
  skills?: string[]
}

export interface TechnicianUpdate {
  name?: string
  phone?: string | null
  email?: string | null
  active?: boolean
  service_area?: string | null
  skills?: string[]
}

export interface Visit {
  id: string
  incident_id: string
  technician_id?: string | null
  scheduled_start?: string | null
  scheduled_end?: string | null
  status: VisitStatus | string
  address?: string | null
  notes?: string | null
  created_at?: string
  updated_at?: string
}

export interface VisitFilters {
  incident_id?: string
  technician_id?: string
  status?: string
  limit?: number
}

export interface CalendarVisitFilters {
  start_date: string
  end_date: string
  technician_id?: string
  status?: string
}

export interface VisitCreate {
  incident_id: string
  technician_id?: string | null
  scheduled_start?: string | null
  scheduled_end?: string | null
  status?: VisitStatus
  address?: string | null
  notes?: string | null
}

export interface VisitUpdate {
  technician_id?: string | null
  scheduled_start?: string | null
  scheduled_end?: string | null
  status?: VisitStatus
  address?: string | null
  notes?: string | null
}

export interface DashboardSummary {
  incidents: {
    total: number
    pending_review: number
    urgent: number
    ready_for_scheduling: number
  }
  human_review: {
    open: number
    urgent: number
  }
  visits: {
    total: number
    scheduled: number
    in_progress: number
    completed: number
    today: number
    scheduled_this_week: number
  }
  technicians: {
    total: number
    active: number
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
export const REQUIRE_LOGIN = (import.meta.env.VITE_REQUIRE_LOGIN ?? 'true') !== 'false'
const ADMIN_API_KEY_STORAGE_KEY = 'hermes_admin_api_key'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getStoredAdminApiKey(): string {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(ADMIN_API_KEY_STORAGE_KEY) ?? ''
}

export function setStoredAdminApiKey(apiKey: string): void {
  window.localStorage.setItem(ADMIN_API_KEY_STORAGE_KEY, apiKey)
}

export function clearStoredAdminApiKey(): void {
  window.localStorage.removeItem(ADMIN_API_KEY_STORAGE_KEY)
}

export function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

function buildHeaders(includeJson = false): HeadersInit {
  const headers: Record<string, string> = {}
  if (includeJson) {
    headers['Content-Type'] = 'application/json'
  }

  const adminApiKey = getStoredAdminApiKey()
  if (adminApiKey) {
    headers['X-Admin-API-Key'] = adminApiKey
  }

  return headers
}

async function parseApiResponse<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    const message = response.status === 401 ? 'No autorizado' : `${errorMessage} (${response.status})`
    throw new ApiError(message, response.status)
  }

  return response.json()
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetch(`${API_BASE_URL}/dashboard/summary`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<DashboardSummary>(response, 'No se pudo cargar el dashboard')
}

export async function fetchIncidents(filters: IncidentFilters = {}): Promise<Incident[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.limit) params.set('limit', String(filters.limit))

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/incidents${query ? `?${query}` : ''}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Incident[]>(response, 'No se pudieron cargar las incidencias')
}

export async function fetchIncident(incidentId: string): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/incidents/${encodeURIComponent(incidentId)}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Incident>(response, 'No se pudo cargar la incidencia')
}

export async function updateIncident(
  incidentId: string,
  update: IncidentUpdate,
): Promise<Incident> {
  const response = await fetch(`${API_BASE_URL}/incidents/${encodeURIComponent(incidentId)}`, {
    method: 'PATCH',
    headers: buildHeaders(true),
    body: JSON.stringify(update),
  })

  return parseApiResponse<Incident>(response, 'No se pudo guardar la incidencia')
}

export async function fetchDecisionRecords(
  filters: DecisionRecordFilters = {},
): Promise<DecisionRecord[]> {
  const params = new URLSearchParams()
  if (filters.conversation_id) params.set('conversation_id', filters.conversation_id)
  if (filters.action_type) params.set('action_type', filters.action_type)
  if (filters.fallback_used !== undefined) params.set('fallback_used', String(filters.fallback_used))
  if (filters.limit) params.set('limit', String(filters.limit))

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/audit/decisions${query ? `?${query}` : ''}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<DecisionRecord[]>(response, 'No se pudo cargar la auditoría')
}

export async function fetchHumanReviewItems(
  filters: HumanReviewFilters = {},
): Promise<HumanReviewItem[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.limit) params.set('limit', String(filters.limit))

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/human-review${query ? `?${query}` : ''}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<HumanReviewItem[]>(
    response,
    'No se pudo cargar la cola de revisión',
  )
}

export async function fetchHumanReviewItem(itemId: string): Promise<HumanReviewItem> {
  const response = await fetch(`${API_BASE_URL}/human-review/${encodeURIComponent(itemId)}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<HumanReviewItem>(
    response,
    'No se pudo cargar el elemento de revisión',
  )
}

export async function updateHumanReviewItem(
  itemId: string,
  update: HumanReviewUpdate,
): Promise<HumanReviewItem> {
  const response = await fetch(`${API_BASE_URL}/human-review/${encodeURIComponent(itemId)}`, {
    method: 'PATCH',
    headers: buildHeaders(true),
    body: JSON.stringify(update),
  })

  return parseApiResponse<HumanReviewItem>(
    response,
    'No se pudo guardar el elemento de revisión',
  )
}

export async function fetchTechnicians(
  filters: TechnicianFilters = {},
): Promise<Technician[]> {
  const params = new URLSearchParams()
  if (filters.active !== undefined) params.set('active', String(filters.active))
  if (filters.limit) params.set('limit', String(filters.limit))

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/technicians${query ? `?${query}` : ''}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Technician[]>(response, 'No se pudieron cargar los técnicos')
}

export async function createTechnician(
  technician: TechnicianCreate,
): Promise<Technician> {
  const response = await fetch(`${API_BASE_URL}/technicians`, {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify(technician),
  })

  return parseApiResponse<Technician>(response, 'No se pudo crear el técnico')
}

export async function fetchTechnician(technicianId: string): Promise<Technician> {
  const response = await fetch(`${API_BASE_URL}/technicians/${encodeURIComponent(technicianId)}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Technician>(response, 'No se pudo cargar el técnico')
}

export async function updateTechnician(
  technicianId: string,
  update: TechnicianUpdate,
): Promise<Technician> {
  const response = await fetch(`${API_BASE_URL}/technicians/${encodeURIComponent(technicianId)}`, {
    method: 'PATCH',
    headers: buildHeaders(true),
    body: JSON.stringify(update),
  })

  return parseApiResponse<Technician>(response, 'No se pudo guardar el técnico')
}

export async function fetchVisits(filters: VisitFilters = {}): Promise<Visit[]> {
  const params = new URLSearchParams()
  if (filters.incident_id) params.set('incident_id', filters.incident_id)
  if (filters.technician_id) params.set('technician_id', filters.technician_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.limit) params.set('limit', String(filters.limit))

  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/visits${query ? `?${query}` : ''}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Visit[]>(response, 'No se pudieron cargar las visitas')
}

export async function listCalendarVisits(filters: CalendarVisitFilters): Promise<Visit[]> {
  const params = new URLSearchParams()
  params.set('start_date', filters.start_date)
  params.set('end_date', filters.end_date)
  if (filters.technician_id) params.set('technician_id', filters.technician_id)
  if (filters.status) params.set('status', filters.status)

  const response = await fetch(`${API_BASE_URL}/calendar/visits?${params.toString()}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Visit[]>(response, 'No se pudo cargar el calendario')
}

export async function createVisit(visit: VisitCreate): Promise<Visit> {
  const response = await fetch(`${API_BASE_URL}/visits`, {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify(visit),
  })

  return parseApiResponse<Visit>(response, 'No se pudo crear la visita')
}

export async function fetchVisit(visitId: string): Promise<Visit> {
  const response = await fetch(`${API_BASE_URL}/visits/${encodeURIComponent(visitId)}`, {
    headers: buildHeaders(),
  })

  return parseApiResponse<Visit>(response, 'No se pudo cargar la visita')
}

export async function updateVisit(
  visitId: string,
  update: VisitUpdate,
): Promise<Visit> {
  const response = await fetch(`${API_BASE_URL}/visits/${encodeURIComponent(visitId)}`, {
    method: 'PATCH',
    headers: buildHeaders(true),
    body: JSON.stringify(update),
  })

  return parseApiResponse<Visit>(response, 'No se pudo guardar la visita')
}
