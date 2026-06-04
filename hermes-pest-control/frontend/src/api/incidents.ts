import { client } from './client'
import { Incident } from './types'

/**
 * Obtiene la lista de incidentes.
 * 
 * @param filters Filtros de búsqueda (status, priority, etc.)
 * @returns Lista de incidentes
 */
export async function listIncidents(
  filters?: Record<string, any>
): Promise<Incident[]> {
  const response = await client.get<Incident[]>('/incidents', {
    params: filters,
  })
  return response.data
}

/**
 * Obtiene el detalle de un incidente por su ID.
 * 
 * @param id ID del incidente
 * @returns Detalle del incidente
 */
export async function getIncident(id: string): Promise<Incident> {
  const response = await client.get<Incident>(`/incidents/${encodeURIComponent(id)}`)
  return response.data
}

/**
 * Actualiza parcialmente un incidente.
 * 
 * @param id ID del incidente
 * @param payload Atributos a actualizar (status, priority, internal_notes)
 * @returns Incidente actualizado
 */
export async function updateIncident(
  id: string,
  payload: Partial<Incident>
): Promise<Incident> {
  const response = await client.patch<Incident>(
    `/incidents/${encodeURIComponent(id)}`,
    payload
  )
  return response.data
}
