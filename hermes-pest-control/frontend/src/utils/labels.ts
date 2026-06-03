const actionLabels: Record<string, string> = {
  reply_only: 'Solo responder',
  collect_missing_data: 'Pedir más datos',
  create_incident: 'Crear incidencia',
  escalate_to_human: 'Pasar a revisión humana',
}

const priorityLabels: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente',
  LOW: 'Baja',
  NORMAL: 'Normal',
  HIGH: 'Alta',
  URGENT: 'Urgente',
}

const severityLabels: Record<string, string> = {
  CRITICAL: 'Crítica',
  HIGH: 'Alta',
  MEDIUM: 'Media',
  LOW: 'Baja',
}

const pestTypeLabels: Record<string, string> = {
  COCKROACH: 'Cucarachas',
  RODENT: 'Roedores',
  ANT: 'Hormigas',
  FLYING_INSECT: 'Insectos voladores',
  STORED_PRODUCT_INSECT: 'Insectos de producto almacenado',
  UNKNOWN: 'Desconocida',
}

const visitTypeLabels: Record<string, string> = {
  URGENT_TREATMENT: 'Tratamiento urgente',
  TREATMENT: 'Tratamiento',
  INSPECTION: 'Inspección',
  FOLLOW_UP: 'Seguimiento',
  HUMAN_REVIEW: 'Revisión humana',
}

const technicianLevelLabels: Record<string, string> = {
  JUNIOR: 'Junior',
  STANDARD: 'Estándar',
  SENIOR: 'Senior',
  SPECIALIST: 'Especialista',
}

const dispatchBucketLabels: Record<string, string> = {
  URGENT_24H: 'Urgente 24h',
  NEXT_48H: 'Próximas 48h',
  THIS_WEEK: 'Esta semana',
  PLANNED: 'Planificada',
  MANUAL_REVIEW: 'Revisión manual',
}

const slaStatusLabels: Record<string, string> = {
  ON_TRACK: 'Dentro de SLA',
  AT_RISK: 'En riesgo',
  BREACHED: 'Vencida',
  COMPLETED: 'Completada',
}

const statusLabels: Record<string, string> = {
  new: 'Nueva',
  pending_review: 'Pendiente de revisión',
  waiting_for_client_data: 'Esperando datos del cliente',
  ready_for_scheduling: 'Lista para programar',
  scheduled: 'Programada',
  in_progress: 'En curso',
  completed: 'Completada',
  follow_up_pending: 'Seguimiento pendiente',
  closed: 'Cerrada',
  cancelled: 'Cancelada',
  draft: 'Borrador',
  open: 'Abierta',
  in_review: 'En revisión',
  resolved: 'Resuelta',
  dismissed: 'Descartada',
  reviewed: 'Revisado',
  archived: 'Archivado',
  proposed: 'Propuesta',
  approved: 'Aprobada',
  rejected: 'Rechazada',
  needs_more_info: 'Necesita más información',
}

const agreementLabels: Record<string, string> = {
  full_agreement: 'Coinciden',
  differences_detected: 'Hay diferencias',
  shadow_error: 'Error de IA en sombra',
}

const channelLabels: Record<string, string> = {
  telegram: 'Telegram',
  whatsapp: 'WhatsApp',
  webchat: 'Webchat',
  email: 'Email',
  sms: 'SMS',
}

const documentTypeLabels: Record<string, string> = {
  incident_summary: 'Resumen de incidencia',
  technician_brief: 'Brief para técnico',
  post_treatment_recommendations: 'Recomendaciones posteriores',
  work_report_draft: 'Borrador de parte de trabajo',
}

const generatedByLabels: Record<string, string> = {
  system: 'Sistema',
  admin: 'Administrador',
  agent_proposal: 'Propuesta de IA',
}

const hermesModeLabels: Record<string, string> = {
  mock: 'Mock',
  real: 'Real',
  llm: 'LLM real',
  local: 'Local',
  fake: 'Fake',
}

const reasonLabels: Record<string, string> = {
  fallback_used: 'Respuesta segura usada',
  agent_escalation: 'Escalado por Hermes',
  urgent_priority: 'Prioridad urgente',
  sensitive_case: 'Caso sensible',
}

const toolNameLabels: Record<string, string> = {
  'incident.propose_incident': 'Proponer incidencia',
  'calendar.propose_event': 'Proponer visita en calendario',
  'gmail.create_draft': 'Borrador de email',
  'gmail.send_email': 'Enviar email',
  'telegram.draft_message': 'Borrador de Telegram',
  'whatsapp.draft_message': 'Borrador de WhatsApp',
  'firestore.write': 'Escritura directa en Firestore',
}

const providerLabels: Record<string, string> = {
  incident_service: 'Servicio de incidencias',
  internal: 'Sistema interno',
  calendar: 'Calendario',
  gmail: 'Gmail',
  telegram: 'Telegram',
  whatsapp: 'WhatsApp',
  firestore: 'Firestore',
}

const riskLevelLabels: Record<string, string> = {
  '0': 'Nivel 0 · Lectura/propuesta',
  '1': 'Nivel 1 · Borrador',
  '2': 'Nivel 2 · Acción segura',
  '3': 'Nivel 3 · Requiere aprobación',
  '4': 'Nivel 4 · Autonomía limitada',
  '5': 'Nivel 5 · No permitido',
}

const toolDecisionLabels: Record<string, string> = {
  allow: 'Permitida como propuesta',
  deny: 'Denegada',
  require_human_approval: 'Requiere revisión humana',
  convert_to_draft: 'Convertida a borrador',
  require_more_data: 'Necesita más datos',
}

const executionStatusLabels: Record<string, string> = {
  not_executed: 'No ejecutada',
  blocked: 'Bloqueada',
  draft_proposed: 'Borrador propuesto',
  pending_human_approval: 'Pendiente de aprobación humana',
  requires_more_data: 'Requiere más datos',
  allowed_not_executed: 'Permitida sin ejecutar',
  executed: 'Ejecutada',
}

export function labelFromMap(value: string | null | undefined, labels: Record<string, string>): string {
  if (!value || !value.trim()) return 'Sin dato'
  return labels[value] ?? value
}

export function formatAction(value: string | null | undefined): string {
  return labelFromMap(value, actionLabels)
}

export function formatPriority(value: string | null | undefined): string {
  return labelFromMap(value, priorityLabels)
}

export function formatSeverity(value: string | null | undefined): string {
  return labelFromMap(value, severityLabels)
}

export function formatPestType(value: string | null | undefined): string {
  return labelFromMap(value, pestTypeLabels)
}

export function formatVisitType(value: string | null | undefined): string {
  return labelFromMap(value, visitTypeLabels)
}

export function formatTechnicianLevel(value: string | null | undefined): string {
  return labelFromMap(value, technicianLevelLabels)
}

export function formatDispatchBucket(value: string | null | undefined): string {
  return labelFromMap(value, dispatchBucketLabels)
}

export function formatSlaStatus(value: string | null | undefined): string {
  return labelFromMap(value, slaStatusLabels)
}

export function formatStatus(value: string | null | undefined): string {
  return labelFromMap(value, statusLabels)
}

export function formatAgreement(value: string | null | undefined): string {
  return labelFromMap(value, agreementLabels)
}

export function formatChannel(value: string | null | undefined): string {
  return labelFromMap(value, channelLabels)
}

export function formatDocumentType(value: string | null | undefined): string {
  return labelFromMap(value, documentTypeLabels)
}

export function formatGeneratedBy(value: string | null | undefined): string {
  return labelFromMap(value, generatedByLabels)
}

export function formatHermesMode(value: string | null | undefined): string {
  return labelFromMap(value, hermesModeLabels)
}

export function formatReason(value: string | null | undefined): string {
  return labelFromMap(value, reasonLabels)
}

export function formatToolName(value: string | null | undefined): string {
  return labelFromMap(value, toolNameLabels)
}

export function formatToolProvider(value: string | null | undefined): string {
  return labelFromMap(value, providerLabels)
}

export function formatRiskLevel(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return 'Sin dato'
  return labelFromMap(String(value), riskLevelLabels)
}

export function formatToolDecision(value: string | null | undefined): string {
  return labelFromMap(value, toolDecisionLabels)
}

export function formatReviewStatus(value: string | null | undefined): string {
  return labelFromMap(value, statusLabels)
}

export function formatExecutionStatus(value: string | null | undefined): string {
  return labelFromMap(value, executionStatusLabels)
}

export function formatBooleanYesNo(value: boolean | null | undefined): string {
  if (value === true) return 'Sí'
  if (value === false) return 'No'
  return 'Sin dato'
}

export function formatFallback(value: boolean | null | undefined): string {
  if (value === true) return 'Sí, se usó respuesta segura'
  if (value === false) return 'No'
  return 'Sin dato'
}

export function formatPlainValue(value: string | null | undefined): string {
  return value && value.trim() ? value : 'Sin dato'
}

export function agreementClass(value: string | null | undefined): string {
  if (value === 'full_agreement') return 'agreement-ok'
  if (value === 'shadow_error') return 'agreement-error'
  if (value === 'differences_detected') return 'agreement-warning'
  return 'agreement-neutral'
}

export function shadowInterpretation(value: string | null | undefined): string {
  if (value === 'full_agreement') return 'La IA coincide con el sistema actual en este caso.'
  if (value === 'differences_detected') {
    return 'La IA propone una decisión distinta. Conviene revisar si su criterio es mejor o peor.'
  }
  if (value === 'shadow_error') {
    return 'La IA no pudo evaluarse correctamente. El sistema principal no se vio afectado.'
  }
  return 'No hay interpretación disponible para este registro.'
}

export function differenceText(difference: string): string {
  const labels: Record<string, string> = {
    action_type: 'La IA habría tomado una acción distinta.',
    priority: 'La IA ha detectado una prioridad distinta.',
    pest_type: 'La IA no ha identificado la misma plaga.',
    should_create: 'La IA no coincide sobre si se debería crear incidencia.',
    shadow_fallback: 'La IA usó una respuesta segura en sombra.',
  }
  return labels[difference] ?? `Diferencia detectada: ${difference}`
}

export function normalizeDifferences(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item))
  if (value && typeof value === 'object') return Object.keys(value as Record<string, unknown>)
  return []
}
