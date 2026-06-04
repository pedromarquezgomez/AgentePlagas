<script setup lang="ts">
import SectionCard from './SectionCard.vue'

defineProps<{
  provider: string
  model: string
}>()
</script>

<template>
  <SectionCard 
    title="Motor de IA Activo" 
    subtitle="Proveedor y modelo de lenguaje actualmente en uso"
  >
    <div class="engine-status-container">
      <div class="status-pulse-badge">
        <span class="pulse-dot"></span>
        <span class="status-text">ONLINE</span>
      </div>

      <div class="engine-meta-row">
        <span class="meta-label">Proveedor:</span>
        <span class="meta-value uppercase font-mono">{{ provider }}</span>
      </div>

      <div class="engine-meta-row">
        <span class="meta-label">Modelo:</span>
        <span class="meta-value font-mono">{{ model }}</span>
      </div>
    </div>

    <div class="engine-footer-desc">
      Estadísticas recolectadas de forma segura y validadas por el servidor.
    </div>
  </SectionCard>
</template>

<style scoped>
.engine-status-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 4px;
  flex: 1;
}

.status-pulse-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 4px 8px;
  border-radius: 6px;
  align-self: flex-start;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background-color: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-text {
  font-size: 9px;
  font-weight: 800;
  color: #34d399;
  letter-spacing: 0.05em;
}

@keyframes pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.engine-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  border-bottom: 1px solid #27272a;
  padding-bottom: 8px;
}

.meta-label {
  color: #71717a;
}

.meta-value {
  color: #f4f4f5;
  font-weight: 700;
}

.engine-footer-desc {
  font-size: 9px;
  color: #52525b;
  margin-top: 16px;
}
</style>
