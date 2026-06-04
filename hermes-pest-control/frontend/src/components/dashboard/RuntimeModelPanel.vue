<script setup lang="ts">
defineProps<{
  provider: string
  model: string
}>()
</script>

<template>
  <div class="metrics-block">
    <div>
      <h3 class="block-title">Motor de IA Activo</h3>
      <p class="block-subtitle">Proveedor y modelo de lenguaje actualmente en uso</p>
    </div>

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

.engine-status-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
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
