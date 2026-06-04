<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  approved: number
  rejected: number
  pending: number
}>()

const total = computed(() => {
  const sum = props.approved + props.rejected + props.pending
  return sum === 0 ? 1 : sum
})

const percentApproved = computed(() => {
  return Math.round((props.approved / total.value) * 100)
})

const percentRejected = computed(() => {
  return Math.round((props.rejected / total.value) * 100)
})

const percentPending = computed(() => {
  return 100 - percentApproved.value - percentRejected.value
})

// Offsets for the SVG donut
const offsetRejected = computed(() => {
  return -percentApproved.value
})

const offsetPending = computed(() => {
  return -(percentApproved.value + percentRejected.value)
})
</script>

<template>
  <div class="metrics-block flex-between">
    <div>
      <h3 class="block-title">Decisiones del Motor de IA</h3>
      <p class="block-subtitle">Salud de la distribución de autorizaciones y bloqueos</p>
    </div>

    <div class="donut-chart-wrapper">
      <div class="donut-svg-wrapper">
        <svg class="donut-svg" viewBox="0 0 36 36">
          <!-- Background track -->
          <circle class="donut-bg" cx="18" cy="18" r="15.9155" stroke-width="3.5" />
          
          <!-- Approved (Green) -->
          <circle class="donut-fill approved" cx="18" cy="18" r="15.9155" stroke-width="4.5" 
            :stroke-dasharray="`${percentApproved}, 100`" stroke-dashoffset="0" />
          
          <!-- Rejected (Red) -->
          <circle class="donut-fill rejected" cx="18" cy="18" r="15.9155" stroke-width="4.5" 
            :stroke-dasharray="`${percentRejected}, 100`" :stroke-dashoffset="offsetRejected" />
          
          <!-- Pending (Amber) -->
          <circle class="donut-fill pending" cx="18" cy="18" r="15.9155" stroke-width="4.5" 
            :stroke-dasharray="`${percentPending}, 100`" :stroke-dashoffset="offsetPending" />
        </svg>
        <div class="donut-labels">
          <span class="donut-value">{{ approved + rejected + pending }}</span>
          <span class="donut-sub">Decisiones</span>
        </div>
      </div>
    </div>

    <div class="donut-legend">
      <div class="legend-item">
        <span class="legend-dot green"></span>
        <span class="legend-text">Aprobadas: {{ percentApproved }}%</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot red"></span>
        <span class="legend-text">Rechazadas: {{ percentRejected }}%</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot amber"></span>
        <span class="legend-text">Pendientes: {{ percentPending }}%</span>
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

.donut-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 20px 0;
}

.donut-svg-wrapper {
  position: relative;
  width: 112px;
  height: 112px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-bg {
  fill: none;
  stroke: #27272a;
}

.donut-fill {
  fill: none;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease, stroke-dashoffset 0.5s ease;
}

.donut-fill.approved {
  stroke: #10b981; /* green-500 */
}

.donut-fill.rejected {
  stroke: #ef4444; /* red-500 */
}

.donut-fill.pending {
  stroke: #f59e0b; /* amber-500 */
}

.donut-labels {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-value {
  font-size: 26px;
  font-weight: 800;
  color: #f4f4f5;
  line-height: 1;
}

.donut-sub {
  font-size: 8px;
  text-transform: uppercase;
  color: #71717a;
  letter-spacing: 0.05em;
  margin-top: 2px;
  font-weight: 600;
}

.donut-legend {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  border-top: 1px solid #27272a;
  padding-top: 12px;
  gap: 8px;
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

.legend-dot.amber {
  background: #f59e0b;
}

.legend-text {
  color: #a1a1aa;
}
</style>
