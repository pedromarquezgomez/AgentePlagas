<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import VisitDetail from '../components/VisitDetail.vue'

const props = defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/visits')
}

function handleCreated(newVisitId: string) {
  void router.replace(`/visits/${encodeURIComponent(newVisitId)}`)
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="visit-detail-page">
    <Breadcrumbs
      parentPath="/visits"
      parentLabel="Visitas"
      :currentLabel="id === 'new' ? 'Nueva Visita' : 'Detalle de Visita'"
    />

    <VisitDetail
      :visit-id="id"
      @back="handleBack"
      @created="handleCreated"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.visit-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
