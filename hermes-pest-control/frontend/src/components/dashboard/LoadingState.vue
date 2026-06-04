<script setup lang="ts">
withDefaults(defineProps<{
  message?: string
}>(), {
  message: 'Cargando datos...'
})
</script>

<template>
  <div class="loading-state-container">
    <div class="spinner-wrapper">
      <div class="outer-spinner"></div>
      <div class="inner-pulse"></div>
    </div>
    <p class="loading-message font-mono">{{ message }}</p>
  </div>
</template>

<style scoped>
.loading-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.spinner-wrapper {
  position: relative;
  width: 40px;
  height: 40px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.outer-spinner {
  width: 100%;
  height: 100%;
  border: 2.5px solid rgba(52, 211, 153, 0.1); /* emerald shadow */
  border-top-color: #10b981; /* emerald-500 */
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.inner-pulse {
  position: absolute;
  width: 12px;
  height: 12px;
  background-color: #10b981;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.loading-message {
  font-size: 11px;
  font-weight: 700;
  color: #71717a; /* zinc-500 */
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(0.85);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
  }
}
</style>
