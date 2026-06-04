<script setup lang="ts">
import type { RuntimeStats } from '../../api/types'
import KpiCard from './KpiCard.vue'

defineProps<{
  stats: RuntimeStats | null
}>()
</script>

<template>
  <div v-if="stats" class="kpi-grid">
    <KpiCard
      title="Peticiones Realizadas"
      :value="stats.requests"
      description="Invocaciones totales al modelo LLM"
      iconType="comments"
    />
    <KpiCard
      title="Latencia de Inferencia"
      :value="stats.avg_latency_ms + ' ms'"
      description="Tiempo promedio de respuesta del LLM"
      iconType="sla"
      variant="emerald"
    />
    <KpiCard
      title="Fallbacks de Respaldo"
      :value="stats.fallbacks"
      :description="stats.fallbacks > 0 ? 'Redirecciones por error o tiempo límite' : 'Sin redirecciones a motor secundario'"
      iconType="incidents"
      :variant="stats.fallbacks > 0 ? 'danger' : 'default'"
    />
    <KpiCard
      title="Tokens Totales"
      :value="stats.total_tokens"
      description="Volumen total de tokens procesados"
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
