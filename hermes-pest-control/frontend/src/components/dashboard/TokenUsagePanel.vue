<script setup lang="ts">
import { computed } from 'vue'
import SectionCard from './SectionCard.vue'

const props = defineProps<{
  promptTokens: number
  completionTokens: number
  totalTokens: number
}>()

const promptTokenPercent = computed(() => {
  if (props.totalTokens === 0) return 50
  return Math.round((props.promptTokens / props.totalTokens) * 100)
})

const completionTokenPercent = computed(() => {
  return 100 - promptTokenPercent.value
})
</script>

<template>
  <SectionCard 
    title="Distribución y Consumo de Tokens" 
    subtitle="Volumen de datos de entrada frente a datos de salida procesados"
    :colSpan="2"
  >
    <div class="tokens-distribution-container">
      <div class="token-metric-item">
        <div class="token-meta">
          <span class="token-type">Prompt Tokens (Entrada/Contexto)</span>
          <span class="token-count font-mono">{{ promptTokens }} ({{ promptTokenPercent }}%)</span>
        </div>
        <div class="token-bar-track">
          <div class="token-bar-fill prompt-fill" :style="{ width: promptTokenPercent + '%' }"></div>
        </div>
      </div>

      <div class="token-metric-item">
        <div class="token-meta">
          <span class="token-type">Completion Tokens (Salida/Generación)</span>
          <span class="token-count font-mono">{{ completionTokens }} ({{ completionTokenPercent }}%)</span>
        </div>
        <div class="token-bar-track">
          <div class="token-bar-fill completion-fill" :style="{ width: completionTokenPercent + '%' }"></div>
        </div>
      </div>
    </div>
    
    <div class="token-total-footer">
      <span class="total-text font-mono">Consumo Acumulado: {{ totalTokens }} tokens</span>
    </div>
  </SectionCard>
</template>

<style scoped>
.tokens-distribution-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 4px;
  flex: 1;
}

.token-metric-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.token-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #a1a1aa;
}

.token-type {
  font-weight: 500;
  color: #d4d4d8;
}

.token-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.token-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.prompt-fill {
  background: linear-gradient(90deg, #0284c7, #38bdf8); /* sky-600 to sky-400 */
}

.completion-fill {
  background: linear-gradient(90deg, #7c3aed, #a855f7); /* violet-600 to purple-500 */
}

.token-total-footer {
  margin-top: 16px;
  border-top: 1px solid #27272a;
  padding-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.total-text {
  background: #09090b;
  border: 1px solid #27272a;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 10px;
  color: #e4e4e7;
  font-weight: 700;
}
</style>
