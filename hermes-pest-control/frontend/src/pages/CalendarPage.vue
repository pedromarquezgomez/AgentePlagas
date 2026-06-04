<script setup lang="ts">
import { useRouter } from 'vue-router'
import PageHeader from '../components/dashboard/PageHeader.vue'
import CalendarPanel from '../components/CalendarPanel.vue'

const router = useRouter()

function openVisit(visitId: string) {
  void router.push(`/visits/${encodeURIComponent(visitId)}`)
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="calendar-page">
    <PageHeader
      title="Calendario de Visitas"
      subtitle="Visualización de visitas técnicas planificadas y asignaciones horarias."
    />

    <CalendarPanel
      @open="openVisit"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.calendar-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
