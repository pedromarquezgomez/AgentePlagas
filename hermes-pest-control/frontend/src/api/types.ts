export interface Incident {
  id: string
  conversation_id: string | null
  channel: string
  pest_type: string | null
  location: string | null
  affected_area: string | null
  priority: string
  operational_priority?: string | null
  status: string
  summary: string | null
  internal_notes?: string | null
  confidence?: string | null
  severity?: string | null
  response_hours?: number | null
  assessment_reason?: string | null
  visit_type?: string | null
  technician_level?: string | null
  dispatch_bucket?: string | null
  sla_hours?: number | null
  sla_status?: string | null
  elapsed_hours?: number | null
  remaining_hours?: number | null
  breach_hours?: number | null
  created_at?: string
  updated_at?: string
  metadata?: Record<string, any> | null
}

export interface AnalyticsOverview {
  total_conversations: number
  incidents_created: number
  visits_proposed: number
  visits_confirmed: number
  gmail_drafts_proposed: number
  gmail_drafts_approved: number
  human_reviews_required: number
  human_reviews_completed: number
  fallback_count: number
  sla_breaches: number
  cancelled_incidents: number
  closed_incidents: number
  avg_llm_latency_ms: number
  estimated_prompt_tokens: number
  estimated_completion_tokens: number
  estimated_total_tokens: number
  estimated_llm_cost_usd: number
}

export interface ToolExecution {
  id: string
  tool_request_id: string
  tool_decision_id: string
  trace_id: string
  conversation_id: string
  tool_name: string
  provider: string
  action: string
  risk_level: number
  requires_approval: boolean
  decision: string
  execution_status: string
  review_status: string
  reviewer_notes?: string | null
  reviewed_by?: string | null
  approved_payload?: Record<string, unknown> | null
  executed: boolean
  external_effect: boolean
  execution_result?: Record<string, unknown> | null
  execution_error?: string | null
  created_at?: string
  updated_at?: string | null
  reviewed_at?: string | null
  executed_at?: string | null
  metadata?: Record<string, unknown>
}

export interface RuntimeStats {
  provider: string
  model: string
  requests: number
  fallbacks: number
  avg_latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    Object.setPrototypeOf(this, ApiError.prototype)
  }
}

export enum AuditEventType {
  PROVIDER_SELECTED = 'provider_selected',
  TOOL_PROPOSED = 'tool_proposed',
  POLICY_EVALUATED = 'policy_evaluated',
  TOOL_EXECUTION_STARTED = 'tool_execution_started',
  TOOL_EXECUTION_COMPLETED = 'tool_execution_completed',
  TOOL_EXECUTION_FAILED = 'tool_execution_failed',
  HUMAN_REVIEW_REQUIRED = 'human_review_required',
  INCIDENT_PRIORITIZED = 'incident_prioritized',
  INCIDENT_DISPATCH_ASSESSED = 'incident_dispatch_assessed',
  INCIDENT_SLA_BREACHED = 'incident_sla_breached',
  VISIT_SLOT_SELECTED = 'visit_slot_selected',
}

export interface AuditEvent {
  event_id: string
  event_type: AuditEventType
  timestamp: string
  execution_id?: string | null
  tool_name?: string | null
  provider?: string | null
  user_id?: string | null
  channel?: string | null
  policy_decision?: string | null
  status?: string | null
  message: string
  metadata?: Record<string, any>
}

