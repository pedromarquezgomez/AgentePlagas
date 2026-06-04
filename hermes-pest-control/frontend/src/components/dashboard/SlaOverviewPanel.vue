<script setup lang="ts">
defineProps<{
  slaComplianceRate: number
  slaOnTimeCount: number
  slaBreaches: number
}>()
</script>

<template>
  <div class="metrics-block flex-between">
    <div>
      <h3 class="block-title">Cumplimiento General SLA</h3>
      <p class="block-subtitle">Métricas de cumplimiento calculadas por el backend</p>
    </div>
    
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
  </div>
</template>

<style scoped>
.metrics-block {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.flex-between {
  justify-content: space-between;
}

.block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a;
  margin: 0;
}

.block-subtitle {
  font-size: 10px;
  color: #52525b;
  margin: 4px 0 0 0;
}

.radial-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 20px 0;
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
