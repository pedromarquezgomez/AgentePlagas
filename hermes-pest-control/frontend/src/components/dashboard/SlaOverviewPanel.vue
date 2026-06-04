<script setup lang="ts">
import SectionCard from './SectionCard.vue'

defineProps<{
  slaComplianceRate: number
  slaOnTimeCount: number
  slaBreaches: number
}>()
</script>

<template>
  <SectionCard 
    title="Cumplimiento General SLA" 
    subtitle="Métricas de cumplimiento calculadas por el backend"
  >
    <div class="radial-chart-wrapper">
      <div class="radial-svg-wrapper">
        <svg class="radial-svg" viewBox="0 0 36 36">
          <path class="radial-bg" stroke-width="3" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          <path class="radial-fill" stroke-width="4.5" :stroke-dasharray="`${slaComplianceRate}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        </svg>
        <div class="radial-labels">
          <span class="radial-value">{{ slaComplianceRate }}%</span>
          <span class="radial-sub">On-Time</span>
        </div>
      </div>
    </div>

    <div class="radial-legend">
      <div class="legend-item">
        <span class="legend-dot green"></span>
        <span class="legend-text">En plazo ({{ slaOnTimeCount }})</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot red"></span>
        <span class="legend-text">Vencidos ({{ slaBreaches }})</span>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.radial-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 12px 0 20px 0;
  flex: 1;
}

.radial-svg-wrapper {
  position: relative;
  width: 112px;
  height: 112px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.radial-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.radial-bg {
  fill: none;
  stroke: #27272a;
}

.radial-fill {
  fill: none;
  stroke: #10b981; /* emerald-500 */
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.radial-labels {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.radial-value {
  font-size: 26px;
  font-weight: 800;
  color: #f4f4f5;
  line-height: 1;
}

.radial-sub {
  font-size: 8px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  margin-top: 2px;
  font-weight: 600;
}

.radial-legend {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  border-top: 1px solid #27272a;
  padding-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.green {
  background: #10b981;
}

.legend-dot.red {
  background: #ef4444;
}

.legend-text {
  color: #a1a1aa;
}
</style>
