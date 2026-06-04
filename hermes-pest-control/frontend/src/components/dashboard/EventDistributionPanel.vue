<script setup lang="ts">
import { computed } from 'vue'
import type { AuditEvent } from '../../api/types'

const props = defineProps<{
  events: AuditEvent[]
}>()

const distribution = computed(() => {
  const counts: Record<string, number> = {}
  props.events.forEach(e => {
    const type = e.event_type || 'unknown'
    counts[type] = (counts[type] || 0) + 1
  })

  const total = props.events.length || 1

  return Object.entries(counts)
    .map(([label, value]) => ({
      label,
      value,
      percent: Math.round((value / total) * 100)
    }))
    .sort((a, b) => b.value - a.value)
})
</script>

<template>
  <div class="metrics-block col-span-2">
    <div>
      <h3 class="block-title">Eventos por Tipo</h3>
      <p class="block-subtitle">Distribución del tipo de operaciones realizadas por el motor y agentes</p>
    </div>

    <div class="events-list">
      <div v-if="distribution.length === 0" class="no-events">
        No hay datos de eventos disponibles.
      </div>
      <div v-for="item in distribution" :key="item.label" class="event-row">
        <div class="event-meta">
          <span class="event-label-text font-mono">{{ item.label }}</span>
          <span class="event-value-text font-mono">{{ item.value }} ({{ item.percent }}%)</span>
        </div>
        <div class="event-bar-track">
          <div class="event-bar-fill" :style="{ width: item.percent + '%' }"></div>
        </div>
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

.col-span-2 {
  grid-column: span 2;
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

.events-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 4px;
}

/* Custom Scrollbar for premium feel */
.events-list::-webkit-scrollbar {
  width: 4px;
}
.events-list::-webkit-scrollbar-track {
  background: #09090b;
}
.events-list::-webkit-scrollbar-thumb {
  background: #27272a;
  border-radius: 2px;
}

.no-events {
  font-size: 11px;
  color: #71717a;
  text-align: center;
  padding: 20px 0;
}

.event-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  align-items: center;
}

.event-label-text {
  color: #d4d4d8;
  font-weight: 500;
}

.event-value-text {
  font-weight: 700;
  color: #f4f4f5;
}

.event-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.event-bar-fill {
  background: linear-gradient(90deg, #0284c7, #38bdf8); /* sky-600 to sky-400 */
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}
</style>
