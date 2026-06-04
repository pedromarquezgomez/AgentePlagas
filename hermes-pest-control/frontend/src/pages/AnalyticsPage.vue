<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getAnalyticsOverview } from '../api/analytics'
import type { AnalyticsOverview } from '../api/types'
import { ApiError } from '../api/types'

const businessMetrics = ref<AnalyticsOverview | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function loadAnalytics() {
  loading.value = true
  error.value = null
  try {
    businessMetrics.value = await getAnalyticsOverview()
  } catch (err) {
    if (err instanceof ApiError) {
      error.value = `${err.message} (Status: ${err.status})`
    } else {
      error.value = err instanceof Error ? err.message : 'Error inesperado al cargar analíticas'
    }
    businessMetrics.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnalytics()
})
</script>

<template>
  <div class="analytics-page">
    <div class="sectionHeader" style="margin-bottom: 24px;">
      <div>
        <span class="eyebrow">Hermes Pest Control</span>
        <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #17202a;">
          Analíticas y Métricas de Negocio
        </h1>
      </div>
      <button 
        class="primaryButton" 
        type="button" 
        :disabled="loading" 
        @click="loadAnalytics"
      >
        {{ loading ? 'Actualizando...' : 'Actualizar' }}
      </button>
    </div>

    <!-- Alertas Operativas -->
    <section v-if="businessMetrics" class="filters" style="margin-bottom: 24px; display: flex; width: 100%;">
      <div 
        v-if="businessMetrics.sla_breaches > 0" 
        class="badge severity-critical" 
        style="padding: 12px 18px; font-size: 14px; border-radius: 8px; width: 100%; text-align: center; justify-content: center; font-weight: 800; border: 1px solid #f1b9aa; display: flex; align-items: center; gap: 8px;"
      >
        🔴 ALERTA ROJA: Se han detectado {{ businessMetrics.sla_breaches }} incumplimientos de SLA en incidentes.
      </div>
      <div 
        v-else-if="businessMetrics.avg_llm_latency_ms > 5000" 
        class="badge" 
        style="padding: 12px 18px; font-size: 14px; border-radius: 8px; width: 100%; text-align: center; justify-content: center; font-weight: 800; background: #ffe3d6; color: #8a2f10; border: 1px solid #fed7aa; display: flex; align-items: center; gap: 8px;"
      >
        ⚠️ ALERTA NARANJA: Latencia media del LLM alta ({{ businessMetrics.avg_llm_latency_ms }} ms).
      </div>
      <div 
        v-else-if="businessMetrics.fallback_count > 0" 
        class="badge" 
        style="padding: 12px 18px; font-size: 14px; border-radius: 8px; width: 100%; text-align: center; justify-content: center; font-weight: 800; background: #fffde7; color: #856404; border: 1px solid #ffeeba; display: flex; align-items: center; gap: 8px;"
      >
        ⚠️ ALERTA AMARILLA: Se han registrado {{ businessMetrics.fallback_count }} fallbacks del LLM a mock.
      </div>
    </section>

    <!-- Grid Principal de KPIs -->
    <section class="contentBand">
      <div v-if="loading && !businessMetrics" class="stateMessage">Cargando métricas...</div>
      <div v-else-if="error" class="stateMessage errorMessage">
        {{ error }}
        <div class="stateAction">
          <button class="secondaryButton" type="button" @click="loadAnalytics">Reintentar</button>
        </div>
      </div>
      <div v-else-if="!businessMetrics" class="stateMessage">
        No se pudieron obtener las métricas de negocio.
      </div>
      <div v-else>
        <div class="dashboardLayout" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">

          <!-- Card Conversaciones -->
          <div class="metricCard" style="min-height: 120px;">
            <span class="metricTitle">CONVERSACIONES TOTALES</span>
            <span class="metricValue">{{ businessMetrics.total_conversations }}</span>
          </div>

          <!-- Card Incidencias -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <span class="metricTitle" style="display: block;">INCIDENCIAS CREADAS</span>
              <span class="metricValue">{{ businessMetrics.incidents_created }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px; display: flex; gap: 12px;">
              <span>Canceladas: <strong style="color: #8a2f10;">{{ businessMetrics.cancelled_incidents }}</strong></span>
              <span>Cerradas: <strong style="color: #273442;">{{ businessMetrics.closed_incidents }}</strong></span>
            </div>
          </div>

          <!-- Card Visitas -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <span class="metricTitle" style="display: block;">VISITAS PROPUESTAS</span>
              <span class="metricValue">{{ businessMetrics.visits_proposed }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px;">
              <span>Confirmadas: <strong style="color: #1e6841;">{{ businessMetrics.visits_confirmed }}</strong></span>
            </div>
          </div>

          <!-- Card Borradores de Gmail -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <span class="metricTitle" style="display: block;">BORRADORES GMAIL</span>
              <span class="metricValue">{{ businessMetrics.gmail_drafts_proposed }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px;">
              <span>Aprobados: <strong style="color: #1e6841;">{{ businessMetrics.gmail_drafts_approved }}</strong></span>
            </div>
          </div>

          <!-- Card Revisiones Humanas -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <span class="metricTitle" style="display: block;">REVISIÓN HUMANA</span>
              <span class="metricValue">{{ businessMetrics.human_reviews_required }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px;">
              <span>Completadas: <strong style="color: #1e6841;">{{ businessMetrics.human_reviews_completed }}</strong></span>
            </div>
          </div>

          <!-- Card SLA breaches -->
          <div 
            class="metricCard" 
            :class="{'sla-breached': businessMetrics.sla_breaches > 0}" 
            style="min-height: 120px;"
          >
            <span class="metricTitle" :style="{color: businessMetrics.sla_breaches > 0 ? '#8b1a1a' : '#405060'}">
              SLA INCUMPLIDOS
            </span>
            <span class="metricValue" :style="{color: businessMetrics.sla_breaches > 0 ? '#8b1a1a' : '#235b8c'}">
              {{ businessMetrics.sla_breaches }}
            </span>
          </div>

          <!-- Card Latencia LLM -->
          <div class="metricCard" style="min-height: 120px;">
            <span class="metricTitle">LATENCIA MEDIA LLM</span>
            <span class="metricValue">
              {{ businessMetrics.avg_llm_latency_ms }} 
              <span style="font-size: 16px; font-weight: 700; color: #5c6773;">ms</span>
            </span>
          </div>

          <!-- Card Coste LLM -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <span class="metricTitle" style="display: block;">COSTE ACUMULADO LLM</span>
              <span class="metricValue">${{ businessMetrics.estimated_llm_cost_usd.toFixed(4) }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px;">
              <span>Fallbacks a Mock: <strong style="color: #8a2f10;">{{ businessMetrics.fallback_count }}</strong></span>
            </div>
          </div>

          <!-- Card Tokens Consumidos -->
          <div class="metricCard" style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between; grid-column: span 2;">
            <div>
              <span class="metricTitle" style="display: block;">TOKENS CONSUMIDOS (TOTAL)</span>
              <span class="metricValue">{{ businessMetrics.estimated_total_tokens }}</span>
            </div>
            <div style="font-size: 13px; color: #5c6773; font-weight: 700; margin-top: 10px; display: flex; gap: 16px;">
              <span>Prompt (Entrada): <strong style="color: #235b8c;">{{ businessMetrics.estimated_prompt_tokens }}</strong></span>
              <span>Completion (Salida): <strong style="color: #1e6841;">{{ businessMetrics.estimated_completion_tokens }}</strong></span>
            </div>
          </div>

        </div>
      </div>
    </section>
  </div>
</template>
