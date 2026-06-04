<script setup lang="ts">
defineProps<{
  channel: string
  pestType: string
  priority: string
  isLoading: boolean
  lastUpdated: string
}>()

const emit = defineEmits<{
  (e: 'update:channel', val: string): void
  (e: 'update:pestType', val: string): void
  (e: 'update:priority', val: string): void
  (e: 'refresh'): void
}>()
</script>

<template>
  <header class="top-filters-bar">
    <!-- Brand / Title context -->
    <div class="brand-container">
      <div class="brand-icon-box">
        <!-- Spider Icon -->
        <svg class="brand-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v18m0-18l-3 3m3-3l3 3M3 12h18m-18 0l3-3m-3 3l3 3M5.22 5.22l13.56 13.56m-13.56 0L18.78 5.22" />
        </svg>
      </div>
      <div class="brand-texts">
        <h1 class="brand-title">
          Hermes Pest AI 
          <span class="badge-saas">SaaS Enterprise</span>
        </h1>
        <p class="brand-subtitle">Plataforma Inteligente de Gestión y Triaje Humano (HITL)</p>
      </div>
    </div>

    <!-- Active Filters & Sync bar -->
    <div class="actions-container">
      <div class="filters-panel">
        <div class="filters-label-group">
          <!-- Filter Icon -->
          <svg class="filter-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
          </svg>
          <span class="filters-label">Filtros:</span>
        </div>
        
        <!-- Channel Select -->
        <select 
          :value="channel" 
          @change="emit('update:channel', ($event.target as HTMLSelectElement).value)"
          class="filter-select border-r"
        >
          <option value="all">Todos los Canales</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="telegram">Telegram</option>
        </select>

        <!-- Pest Select -->
        <select 
          :value="pestType" 
          @change="emit('update:pestType', ($event.target as HTMLSelectElement).value)"
          class="filter-select border-r"
        >
          <option value="all">Todas las Plagas</option>
          <option value="COCKROACH">Cucarachas</option>
          <option value="RODENT">Roedores</option>
          <option value="ANT">Hormigas</option>
          <option value="UNKNOWN">Inciertas / Desconocidas</option>
        </select>

        <!-- Priority Select -->
        <select 
          :value="priority" 
          @change="emit('update:priority', ($event.target as HTMLSelectElement).value)"
          class="filter-select"
        >
          <option value="all">Prioridad: Todas</option>
          <option value="URGENT">Urgente</option>
          <option value="HIGH">Alta</option>
          <option value="NORMAL">Normal</option>
        </select>
      </div>

      <!-- Sync button -->
      <button 
        @click="emit('refresh')" 
        :disabled="isLoading"
        class="sync-button"
      >
        <!-- Rotate Icon -->
        <svg :class="{ 'anim-spin': isLoading }" class="sync-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        Sincronizar
      </button>

      <span class="update-time-text">Actualizado: {{ lastUpdated }}</span>
    </div>
  </header>
</template>

<style scoped>
.top-filters-bar {
  background: #18181b; /* zinc-900 */
  border-bottom: 1px solid #27272a; /* zinc-800 */
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 10;
}

@media (min-width: 768px) {
  .top-filters-bar {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.brand-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon-box {
  background: #059669; /* emerald-600 */
  color: #ffffff;
  padding: 8px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
}

.brand-icon {
  width: 20px;
  height: 20px;
}

.brand-texts {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #f4f4f5; /* zinc-100 */
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge-saas {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.brand-subtitle {
  font-size: 11px;
  color: #a1a1aa; /* zinc-400 */
  margin: 2px 0 0 0;
}

.actions-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.filters-panel {
  display: flex;
  align-items: center;
  background: #09090b; /* zinc-950 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  padding: 4px;
  font-size: 12px;
}

.filters-label-group {
  display: flex;
  align-items: center;
  padding: 0 8px;
  color: #71717a;
  gap: 6px;
}

.filter-icon {
  width: 12px;
  height: 12px;
}

.filters-label {
  font-weight: 600;
}

.filter-select {
  background: transparent;
  border: none;
  color: #e4e4e7;
  outline: none;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
  min-width: unset;
  appearance: auto;
}

.filter-select option {
  background: #18181b;
  color: #e4e4e7;
}

.border-r {
  border-right: 1px solid #27272a;
}

.sync-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  background: #18181b;
  border: 1px solid #27272a;
  color: #d4d4d8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.sync-button:hover {
  background: #27272a;
  color: #f4f4f5;
  border-color: #3f3f46;
}

.sync-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sync-icon {
  width: 14px;
  height: 14px;
}

.anim-spin {
  animation: spin 1s linear infinite;
}

.update-time-text {
  font-size: 10px;
  color: #71717a;
  font-family: 'JetBrains Mono', monospace;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
