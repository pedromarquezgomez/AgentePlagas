<script setup lang="ts">
import { computed } from 'vue'
import type { Technician } from '../../services/api'

const props = withDefaults(
  defineProps<{
    technician: Technician
    visitsCount?: number
    urgentsCount?: number
    nextVisitTime?: string | null
  }>(),
  {
    visitsCount: 0,
    urgentsCount: 0,
    nextVisitTime: null,
  }
)

const emit = defineEmits<{
  select: [techId: string]
}>()

// Lógica de disponibilidad
const workloadState = computed(() => {
  if (!props.technician.active) {
    return { label: 'Inactivo', colorClass: 'state-inactive' }
  }
  if (props.visitsCount >= 4 || props.urgentsCount > 0) {
    return { label: 'Saturado', colorClass: 'state-saturated' }
  }
  if (props.visitsCount >= 1) {
    return { label: 'Ocupado', colorClass: 'state-busy' }
  }
  return { label: 'Disponible', colorClass: 'state-available' }
})
</script>

<template>
  <div class="tech-card" @click="emit('select', technician.id)">
    <div class="tech-header">
      <div class="tech-profile">
        <div class="tech-avatar">
          {{ technician.name.slice(0, 2).toUpperCase() }}
        </div>
        <div>
          <h3 class="tech-name">{{ technician.name }}</h3>
          <p class="tech-area">📍 {{ technician.service_area || 'Sin zona asignada' }}</p>
        </div>
      </div>
      
      <span class="status-indicator" :class="workloadState.colorClass">
        <span class="status-dot"></span>
        {{ workloadState.label }}
      </span>
    </div>

    <div class="tech-body">
      <div class="stat-box">
        <span class="stat-label">Visitas Hoy</span>
        <span class="stat-value" :class="{ 'text-emerald': visitsCount === 0 }">
          {{ visitsCount }}
        </span>
      </div>
      <div class="stat-box">
        <span class="stat-label">Urgentes</span>
        <span class="stat-value" :class="{ 'text-red': urgentsCount > 0 }">
          {{ urgentsCount }}
        </span>
      </div>
      <div class="stat-box full-width">
        <span class="stat-label">Próxima Visita</span>
        <span class="stat-value time-highlight">
          {{ nextVisitTime ? nextVisitTime : 'Sin visitas hoy' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tech-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 18px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.25s ease;
}

.tech-card:hover {
  border-color: #3f3f46;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}

.tech-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.tech-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tech-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #27272a;
  color: #34d399;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.tech-name {
  color: #f4f4f5;
  font-weight: 800;
  font-size: 15px;
  margin: 0;
}

.tech-area {
  color: #71717a;
  font-size: 11px;
  font-weight: 600;
  margin: 2px 0 0 0;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

/* Colores de disponibilidad */
.state-available {
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
}
.state-available .status-dot {
  background: #10b981;
}

.state-busy {
  background: rgba(245, 158, 11, 0.1);
  color: #fbbf24;
}
.state-busy .status-dot {
  background: #f59e0b;
}

.state-saturated {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}
.state-saturated .status-dot {
  background: #ef4444;
}

.state-inactive {
  background: #27272a;
  color: #a1a1aa;
}
.state-inactive .status-dot {
  background: #71717a;
}

.tech-body {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  background: #09090b;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #1f1f23;
}

.stat-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-box.full-width {
  grid-column: 1 / -1;
  border-top: 1px solid #1c1c1e;
  padding-top: 8px;
  margin-top: 4px;
}

.stat-label {
  font-size: 9px;
  color: #71717a;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.stat-value {
  color: #e4e4e7;
  font-size: 14px;
  font-weight: 800;
}

.text-emerald {
  color: #34d399;
}

.text-red {
  color: #f87171;
}

.time-highlight {
  color: #fbbf24;
}
</style>
