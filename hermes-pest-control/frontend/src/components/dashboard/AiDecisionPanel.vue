<script setup lang="ts">
import { computed } from 'vue'
import SectionCard from './SectionCard.vue'

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
  <SectionCard 
    title="Decisiones del Motor de IA" 
    subtitle="Salud de la distribución de autorizaciones y bloqueos"
  >
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
  </SectionCard>
</template>

<style scoped>
.donut-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 12px 0 20px 0;
  flex: 1;
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
