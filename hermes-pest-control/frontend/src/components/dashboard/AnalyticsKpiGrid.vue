<script setup lang="ts">
import type { AnalyticsOverview } from '../../api/types'
import KpiCard from './KpiCard.vue'

defineProps<{
  metrics: AnalyticsOverview | null
  conversionRate: string
}>()
</script>

<template>
  <div v-if="metrics" class="kpi-grid">
    <KpiCard 
      title="Conversaciones Totales"
      :value="metrics.total_conversations"
      description="Acumulado total de mensajes recibidos"
      iconType="comments"
    />
    <KpiCard 
      title="Incidencias Creadas"
      :value="metrics.incidents_created"
      :description="`Cerradas: ${metrics.closed_incidents} | Canceladas: ${metrics.cancelled_incidents}`"
      iconType="incidents"
    />
    <KpiCard 
      title="Tasa de Conversión AI"
      :value="conversionRate + '%'"
      :progressValue="parseFloat(conversionRate)"
      description="Efectividad en creación de incidencias"
      iconType="conversion"
      variant="emerald"
    />
    <KpiCard 
      title="Inversión Coste IA"
      :value="'$' + metrics.estimated_llm_cost_usd.toFixed(3)"
      description="Acumulado por consumo de tokens"
      iconType="cost"
      variant="indigo"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}
</style>
