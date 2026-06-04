import { client } from './client'
import { ToolExecution } from './types'

/**
 * Obtiene la lista de ejecuciones de herramientas de IA.
 * 
 * @param filters Filtros de búsqueda (status, tool_name, etc.)
 * @returns Lista de registros de ejecución de herramientas
 */
export async function listToolExecutions(
  filters?: Record<string, any>
): Promise<ToolExecution[]> {
  const response = await client.get<ToolExecution[]>('/tools/executions', {
    params: filters,
  })
  return response.data
}

/**
 * Aprueba una ejecución de herramienta propuesta.
 * 
 * @param id ID del registro de ejecución
 * @returns Registro actualizado
 */
export async function approveToolExecution(id: string): Promise<ToolExecution> {
  const response = await client.patch<ToolExecution>(
    `/tools/executions/${encodeURIComponent(id)}`,
    { review_status: 'approved' }
  )
  return response.data
}

/**
 * Rechaza una ejecución de herramienta propuesta.
 * 
 * @param id ID del registro de ejecución
 * @returns Registro actualizado
 */
export async function rejectToolExecution(id: string): Promise<ToolExecution> {
  const response = await client.patch<ToolExecution>(
    `/tools/executions/${encodeURIComponent(id)}`,
    { review_status: 'rejected' }
  )
  return response.data
}

/**
 * Ejecuta una acción de herramienta aprobada en el backend.
 * 
 * @param id ID del registro de ejecución
 * @returns Registro actualizado tras la ejecución
 */
export async function executeToolExecution(id: string): Promise<ToolExecution> {
  const response = await client.post<ToolExecution>(
    `/tools/executions/${encodeURIComponent(id)}/execute`
  )
  return response.data
}
