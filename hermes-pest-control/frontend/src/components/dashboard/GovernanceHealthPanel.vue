<script setup lang="ts">
import { computed } from 'vue'
import SectionCard from './SectionCard.vue'

const props = defineProps<{
  pendingCount: number
  avgApprovalTimeSeconds: number // tiempo medio en segundos
  backlogCount: number // pendientes > 24h
  riskLevel: 'HEALTHY' | 'WARNING' | 'CRITICAL'
}>()

const formattedAvgTime = computed(() => {
  const sec = props.avgApprovalTimeSeconds
  if (sec === 0) return '--'
  if (sec < 60) return `${Math.round(sec)}s`
  const min = Math.floor(sec / 60)
  const remainingSec = Math.round(sec % 60)
  if (min < 60) return `${min}m ${remainingSec}s`
  const hrs = Math.floor(min / 60)
  const remainingMin = min % 60
  return `${hrs}h ${remainingMin}m`
})

const riskClass = computed(() => {
  switch (props.riskLevel) {
    case 'CRITICAL': return 'critical'
    case 'WARNING': return 'warning'
    default: return 'healthy'
  }
})
</script>

<template>
  <SectionCard
    title="Salud del Gobierno"
    subtitle="Análisis de rendimiento y cuello de botella del HITL"
  >
    <div class="health-container">
      <div class="risk-badge-container">
        <span class="risk-label">Riesgo Operativo:</span>
        <div class="risk-badge" :class="riskClass">
          <span class="pulse-dot"></span>
          <span class="risk-text">{{ riskLevel }}</span>
        </div>
      </div>

      <div class="health-meta-list">
        <div class="health-meta-row">
          <span class="meta-label">HITL Pendiente:</span>
          <span class="meta-value font-mono" :class="{ 'warning-text': pendingCount > 0 }">
            {{ pendingCount }} tareas
          </span>
        </div>

        <div class="health-meta-row">
          <span class="meta-label">Tiempo Medio Aprobación:</span>
          <span class="meta-value font-mono">{{ formattedAvgTime }}</span>
        </div>

        <div class="health-meta-row">
          <span class="meta-label">Backlog (>24 Horas):</span>
          <span class="meta-value font-mono" :class="{ 'danger-text': backlogCount > 0 }">
            {{ backlogCount }} críticas
          </span>
        </div>
      </div>
    </div>

    <div class="health-footer-desc">
      El riesgo escala a CRITICAL si el backlog supera los 3 elementos.
    </div>
  </SectionCard>
</template>

<style scoped>
.health-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 4px;
  flex: 1;
}

.risk-badge-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-label {
  font-size: 11px;
  color: #a1a1aa;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.risk-badge.healthy {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.2);
  color: #34d399;
}

.risk-badge.healthy .pulse-dot {
  background-color: #10b981;
  animation: pulse-healthy 2s infinite;
}

.risk-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.risk-badge.warning .pulse-dot {
  background-color: #f59e0b;
  animation: pulse-warning 2s infinite;
}

.risk-badge.critical {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.risk-badge.critical .pulse-dot {
  background-color: #ef4444;
  animation: pulse-critical 2s infinite;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.risk-text {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
}

@keyframes pulse-healthy {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 4px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

@keyframes pulse-warning {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 4px rgba(245, 158, 11, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

@keyframes pulse-critical {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.health-meta-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.health-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  border-bottom: 1px solid #27272a;
  padding-bottom: 6px;
}

.meta-label {
  color: #71717a;
}

.meta-value {
  color: #f4f4f5;
  font-weight: 700;
}

.warning-text {
  color: #fbbf24;
}

.danger-text {
  color: #f87171;
}

.health-footer-desc {
  font-size: 9px;
  color: #52525b;
  margin-top: 16px;
}
</style>
