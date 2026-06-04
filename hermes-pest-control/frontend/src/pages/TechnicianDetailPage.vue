<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import TechnicianDetail from '../components/TechnicianDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/technicians')
}

function handleCreated(newTechId: string) {
  void router.replace(`/technicians/${encodeURIComponent(newTechId)}`)
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="technician-detail-page">
    <Breadcrumbs
      parentPath="/technicians"
      parentLabel="Técnicos"
      :currentLabel="id === 'new' ? 'Nuevo Técnico' : 'Detalle de Técnico'"
    />

    <TechnicianDetail
      :technician-id="id"
      @back="handleBack"
      @created="handleCreated"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.technician-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
