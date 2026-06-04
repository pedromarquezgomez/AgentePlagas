<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  currentPath: string
  activeIncidentsCount?: number
  engineStatus?: {
    slaEngine: boolean
    dispatchAssessment: boolean
    policyEngine: boolean
  }
}>()

const emit = defineEmits<{
  (e: 'navigate', path: string): void
}>()

const currentTab = computed(() => {
  if (props.currentPath === '/operations') return 'operations'
  if (props.currentPath === '/ai-performance') return 'ai-performance'
  if (props.currentPath === '/audit') return 'audit'
  if (props.currentPath === '/analytics') return 'analytics'
  if (props.currentPath.startsWith('/incidents')) return 'incidents'
  if (props.currentPath.startsWith('/human-review')) return 'human-review'
  if (props.currentPath.startsWith('/technicians')) return 'technicians'
  if (props.currentPath.startsWith('/visits')) return 'visits'
  if (props.currentPath.startsWith('/calendar')) return 'calendar'
  if (props.currentPath.startsWith('/documents')) return 'documents'
  return 'overview' // default is /dashboard or /
})

const slaEngineOk = computed(() => props.engineStatus?.slaEngine ?? true)
const dispatchOk = computed(() => props.engineStatus?.dispatchAssessment ?? true)
const policyOk = computed(() => props.engineStatus?.policyEngine ?? true)
</script>

<template>
  <nav class="sidebar-nav">
    <div class="navigation-section">
      <!-- Sección 1: Monitoreo & Analítica -->
      <span class="section-title">Paneles del Sistema</span>
      <div class="menu-list">
        <!-- Resumen Ejecutivo -->
        <button 
          @click="emit('navigate', '/dashboard')" 
          :class="{ 'active': currentTab === 'overview' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020 18V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
          </svg>
          Resumen Ejecutivo
        </button>

        <!-- Analíticas -->
        <button 
          @click="emit('navigate', '/analytics')" 
          :class="{ 'active': currentTab === 'analytics' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 107.5 7.5h-7.5V6z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 10.5H21A7.5 7.5 0 0013.5 3v7.5z" />
          </svg>
          Métricas de Negocio
        </button>

        <!-- Rendimiento de la IA -->
        <button 
          @click="emit('navigate', '/ai-performance')" 
          :class="{ 'active': currentTab === 'ai-performance' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m10.5-5.25V4.5m4.5 3.75H21m-1.5 4.5v1.5m-4.5 3.75v1.5m-9-1.5v1.5M4.5 15.75H3m18 0h-1.5m-2.25-12h-9a2.25 2.25 0 00-2.25 2.25v9a2.25 2.25 0 002.25 2.25h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25zM9 9h6v6H9V9z" />
          </svg>
          Rendimiento de la IA
        </button>

        <!-- Auditoría y Gobierno -->
        <button 
          @click="emit('navigate', '/audit')" 
          :class="{ 'active': currentTab === 'audit' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>
          Auditoría y Gobierno
        </button>
      </div>

      <!-- Sección 2: Operaciones del Agente -->
      <span class="section-title" style="margin-top: 12px;">Operaciones del Agente</span>
      <div class="menu-list">
        <!-- Centro Operativo (HITL) -->
        <button 
          @click="emit('navigate', '/operations')" 
          :class="{ 'active': currentTab === 'operations' }"
          class="menu-item justify-between"
        >
          <span class="menu-label-inner">
            <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 .414-.336.75-.75.75H4.5a.75.75 0 01-.75-.75v-4.25m16.5 0a2.25 2.25 0 00-2.25-2.25H18.5m-3 0H5.25A2.25 2.25 0 003 14.15m17.25 0h-3m-14.25 0h3m3 0a2.25 2.25 0 014.5 0M9 3h6m-6 3h6m-9 6h12" />
            </svg>
            Centro Operativo
          </span>
          <span v-if="activeIncidentsCount && activeIncidentsCount > 0" class="badge-count">
            {{ activeIncidentsCount }}
          </span>
        </button>

        <!-- Cola de Revisión Humana -->
        <button 
          @click="emit('navigate', '/human-review')" 
          :class="{ 'active': currentTab === 'human-review' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
          </svg>
          Revisión Humana
        </button>
      </div>

      <!-- Sección 3: Gestión de Datos -->
      <span class="section-title" style="margin-top: 12px;">Gestión de Datos</span>
      <div class="menu-list">
        <!-- Incidencias -->
        <button 
          @click="emit('navigate', '/incidents')" 
          :class="{ 'active': currentTab === 'incidents' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          Incidencias
        </button>

        <!-- Técnicos -->
        <button 
          @click="emit('navigate', '/technicians')" 
          :class="{ 'active': currentTab === 'technicians' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.97 5.97 0 00-.75-2.906m-.75 2.906H18m-6-6a4 4 0 100-8 4 4 0 000 8zm-8 8a9.003 9.003 0 008.361-4.422M8 17.5a9 9 0 01-8.361-4.422m8.361 4.422H0m15.75-8.25a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
          </svg>
          Técnicos
        </button>

        <!-- Visitas -->
        <button 
          @click="emit('navigate', '/visits')" 
          :class="{ 'active': currentTab === 'visits' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.03 0 1.9.693 2.166 1.638m-7.377 0A48.536 48.536 0 0112 3c1.2 0 2.392.05 3.576.152M3 21h18M3 10h18M3 7h18M4.5 3h15A2.25 2.25 0 0121.75 5.25v13.5A2.25 2.25 0 0119.5 21h-15A2.25 2.25 0 014.5 3z" />
          </svg>
          Visitas
        </button>

        <!-- Calendario -->
        <button 
          @click="emit('navigate', '/calendar')" 
          :class="{ 'active': currentTab === 'calendar' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008z" />
          </svg>
          Calendario
        </button>

        <!-- Documentos -->
        <button 
          @click="emit('navigate', '/documents')" 
          :class="{ 'active': currentTab === 'documents' }"
          class="menu-item"
        >
          <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12" />
          </svg>
          Documentos
        </button>
      </div>
    </div>

    <!-- Status Indicators -->
    <div class="status-section">
      <span class="section-title">Estado de Motores (SaaS)</span>
      <div class="status-list">
        <div class="status-indicator">
          <span class="indicator-label">SLAEngine</span>
          <span class="indicator-value" :class="{ 'status-ok': slaEngineOk }">
            <span class="indicator-dot"></span>
            {{ slaEngineOk ? 'Operativo' : 'Desconocido' }}
          </span>
        </div>
        <div class="status-indicator">
          <span class="indicator-label">DispatchAssessment</span>
          <span class="indicator-value" :class="{ 'status-ok': dispatchOk }">
            <span class="indicator-dot"></span>
            {{ dispatchOk ? 'Operativo' : 'Desconocido' }}
          </span>
        </div>
        <div class="status-indicator">
          <span class="indicator-label">PolicyEngine</span>
          <span class="indicator-value" :class="{ 'status-ok': policyOk }">
            <span class="indicator-dot"></span>
            {{ policyOk ? 'Activo' : 'Inactivo' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Tenant Identity Context -->
    <div class="tenant-context">
      <div class="tenant-header">
        <svg class="tenant-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
        </svg>
        <span class="tenant-title">Tenant Activo</span>
      </div>
      <p class="tenant-name">tenant_hermes_global_pest</p>
    </div>
  </nav>
</template>

<style scoped>
.sidebar-nav {
  width: 256px; /* w-64 */
  background: #09090b; /* zinc-950 */
  border-right: 1px solid #18181b; /* zinc-900 */
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}

.navigation-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #3f3f46; /* zinc-700 / zinc-600 */
  display: block;
  padding: 0 12px;
  margin-bottom: 8px;
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  font-size: 12px;
  border-radius: 8px;
  background: transparent;
  border: none;
  color: #a1a1aa; /* zinc-400 */
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.justify-between {
  justify-content: space-between;
}

.menu-label-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-item:hover {
  color: #e4e4e7; /* zinc-200 */
  background: rgba(24, 24, 27, 0.5); /* zinc-900 / 50 */
}

.menu-item.active {
  background: #18181b; /* zinc-900 */
  color: #34d399; /* emerald-400 */
  font-weight: 600;
}

.menu-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.badge-count {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #f87171;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 9999px;
  font-family: 'JetBrains Mono', monospace;
}

.status-section {
  border-top: 1px solid #18181b;
  padding-top: 16px;
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #a1a1aa;
}

.indicator-label {
  font-weight: 400;
}

.indicator-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #71717a;
}

.indicator-value.status-ok {
  color: #34d399; /* emerald-400 */
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #71717a;
}

.status-ok .indicator-dot {
  background: #34d399;
}

.tenant-context {
  background: rgba(24, 24, 27, 0.5);
  border: 1px solid #18181b;
  border-radius: 8px;
  padding: 12px;
  font-size: 10px;
  margin-top: auto;
}

.tenant-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #a1a1aa;
}

.tenant-icon {
  width: 12px;
  height: 12px;
}

.tenant-title {
  font-weight: 700;
  text-transform: uppercase;
}

.tenant-name {
  margin: 0;
  color: #71717a;
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}
</style>
