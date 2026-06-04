<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import IncidentDetail from '../components/IncidentDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/incidents')
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="incident-detail-page">
    <Breadcrumbs
      parentPath="/incidents"
      parentLabel="Incidencias"
      currentLabel="Detalle de Incidencia"
    />

    <IncidentDetail
      :incident-id="id"
      @back="handleBack"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.incident-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
