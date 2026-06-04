import { client } from './client'
import { RuntimeStats } from './types'

/**
 * Obtiene las estadísticas de ejecución del LLM en tiempo real.
 * 
 * @returns Estadísticas agregadas de latencia, peticiones y fallbacks
 */
export async function getRuntimeStats(): Promise<RuntimeStats> {
  const response = await client.get<RuntimeStats>('/evaluation/runtime-stats')
  return response.data
}

/**
 * Obtiene el estado de configuración de los servicios del backend.
 * 
 * @returns Diccionario con el estado de configuración
 */
export async function getConfigStatus(): Promise<Record<string, any>> {
  const response = await client.get<Record<string, any>>('/config/status')
  return response.data
}

/**
 * Obtiene el estado de salud básica del backend (endpoint público).
 * 
 * @returns Estado de salud básico
 */
export async function getHealth(): Promise<{ status: string }> {
  const response = await client.get<{ status: string }>('/health')
  return response.data
}
