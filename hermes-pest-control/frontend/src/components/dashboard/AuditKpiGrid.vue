<script setup lang="ts">
import KpiCard from './KpiCard.vue'

defineProps<{
  totalEvents: number
  toolsExecuted: number
  pendingHitl: number
  approvedHitl: number
  rejectedHitl: number
}>()
</script>

<template>
  <div class="kpi-grid">
    <KpiCard
      title="Eventos Totales"
      :value="totalEvents"
      description="Registrados en la memoria viva del sistema"
      iconType="comments"
    />
    <KpiCard
      title="Tools Ejecutadas"
      :value="toolsExecuted"
      description="Invocaciones completadas con éxito"
      iconType="sla"
      variant="indigo"
    />
    <KpiCard
      title="Pendientes HITL"
      :value="pendingHitl"
      description="Esperando revisión humana de un supervisor"
      iconType="incidents"
      :variant="pendingHitl > 0 ? 'danger' : 'default'"
    />
    <KpiCard
      title="Decisiones Aprobadas"
      :value="approvedHitl"
      description="Acciones operativas permitidas"
      iconType="conversion"
      variant="emerald"
    />
    <KpiCard
      title="Decisiones Rechazadas"
      :value="rejectedHitl"
      description="Acciones operativas bloqueadas"
      iconType="incidents"
      :variant="rejectedHitl > 0 ? 'danger' : 'default'"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
}
</style>
