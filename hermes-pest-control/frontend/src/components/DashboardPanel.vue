<script setup lang="ts">
import type { DashboardSummary } from '../services/api'

const props = defineProps<{
  summary: DashboardSummary | null
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  refresh: []
  open: [path: string]
}>()

const cards = [
  {
    title: 'Incidencias pendientes',
    section: 'incidents',
    metric: 'pending_review',
    path: '/incidents',
  },
  {
    title: 'Incidencias urgentes',
    section: 'incidents',
    metric: 'urgent',
    path: '/incidents',
  },
  {
    title: 'Urgentes 24h',
    section: 'incidents',
    metric: 'urgent_24h',
    path: '/incidents',
  },
  {
    title: 'Alta prioridad',
    section: 'incidents',
    metric: 'high_priority',
    path: '/incidents',
  },
  {
    title: 'Pendientes esta semana',
    section: 'incidents',
    metric: 'pending_this_week',
    path: '/incidents',
  },
  {
    title: 'Revisión humana',
    section: 'incidents',
    metric: 'human_review',
    path: '/human-review',
  },
  {
    title: 'Revisiones humanas abiertas',
    section: 'human_review',
    metric: 'open',
    path: '/human-review',
  },
  {
    title: 'Visitas programadas',
    section: 'visits',
    metric: 'scheduled',
    path: '/visits',
  },
  {
    title: 'Visitas de hoy',
    section: 'visits',
    metric: 'today',
    path: '/calendar',
  },
  {
    title: 'Visitas esta semana',
    section: 'visits',
    metric: 'scheduled_this_week',
    path: '/calendar',
  },
  {
    title: 'Técnicos activos',
    section: 'technicians',
    metric: 'active',
    path: '/technicians',
  },
] as const

function metricValue(card: (typeof cards)[number]): number {
  if (!props.summary) return 0

  switch (card.title) {
    case 'Incidencias pendientes':
      return props.summary.incidents.pending_review
    case 'Incidencias urgentes':
      return props.summary.incidents.urgent
    case 'Urgentes 24h':
      return props.summary.incidents.urgent_24h
    case 'Alta prioridad':
      return props.summary.incidents.high_priority
    case 'Pendientes esta semana':
      return props.summary.incidents.pending_this_week
    case 'Revisión humana':
      return props.summary.incidents.human_review
    case 'Revisiones humanas abiertas':
      return props.summary.human_review.open
    case 'Visitas programadas':
      return props.summary.visits.scheduled
    case 'Visitas de hoy':
      return props.summary.visits.today
    case 'Visitas esta semana':
      return props.summary.visits.scheduled_this_week
    case 'Técnicos activos':
      return props.summary.technicians.active
    default:
      return 0
  }
}

function isEmptySummary(): boolean {
  if (!props.summary) return false
  return (
    props.summary.incidents.total === 0 &&
    props.summary.human_review.open === 0 &&
    props.summary.visits.total === 0 &&
    props.summary.technicians.total === 0
  )
}
</script>

<template>
  <section class="contentBand">
    <div v-if="loading" class="stateMessage">Cargando dashboard...</div>
    <div v-else-if="error" class="stateMessage errorMessage">
      {{ error }}
      <div class="stateAction">
        <button class="secondaryButton" type="button" @click="emit('refresh')">
          Reintentar
        </button>
      </div>
    </div>
    <div v-else-if="summary" class="dashboardLayout">
      <button
        v-for="card in cards"
        :key="card.title"
        class="metricCard"
        type="button"
        @click="emit('open', card.path)"
      >
        <span class="metricTitle">{{ card.title }}</span>
        <span class="metricValue">{{ metricValue(card) }}</span>
      </button>

      <div v-if="isEmptySummary()" class="stateMessage dashboardEmpty">
        No hay actividad operativa todavía.
      </div>
    </div>
  </section>
</template>
