import { client } from './client'
import { AnalyticsOverview } from './types'

/**
 * Obtiene el resumen de métricas operativas de negocio.
 * 
 * @param filters Filtros de búsqueda adicionales (opcionales)
 * @returns Promesa con las métricas agregadas de negocio
 */
export async function getAnalyticsOverview(
  filters?: Record<string, any>
): Promise<AnalyticsOverview> {
  const response = await client.get<AnalyticsOverview>('/analytics/overview', {
    params: filters,
  })
  return response.data
}
