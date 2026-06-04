import { client } from './client'
import { AuditEvent, ToolExecution } from './types'
import { listToolExecutions } from './tools'

/**
 * Obtiene la lista de eventos vivos de auditoría en memoria del backend.
 * 
 * @returns Lista de eventos de auditoría
 */
export async function listAuditEvents(): Promise<AuditEvent[]> {
  const response = await client.get<AuditEvent[]>('/audit/events')
  return response.data
}

/**
 * Obtiene un evento de auditoría en particular por su ID.
 * 
 * @param id ID del evento de auditoría
 * @returns Detalles del evento de auditoría
 */
export async function getAuditEvent(id: string): Promise<AuditEvent> {
  const response = await client.get<AuditEvent>(`/audit/events/${encodeURIComponent(id)}`)
  return response.data
}

/**
 * Obtiene la lista de ejecuciones de herramientas pendientes de revisión (HITL).
 * 
 * @returns Lista de ejecuciones pendientes
 */
export async function listPendingReviews(): Promise<ToolExecution[]> {
  return listToolExecutions({ review_status: 'proposed' })
}
