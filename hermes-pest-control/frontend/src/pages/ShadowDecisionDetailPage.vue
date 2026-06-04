<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import ShadowDecisionDetail from '../components/ShadowDecisionDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/audit')
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="shadow-decision-detail-page">
    <Breadcrumbs
      parentPath="/audit"
      parentLabel="Auditoría y Gobierno"
      currentLabel="Detalle de Decisión en Sombra"
    />

    <ShadowDecisionDetail
      :record-id="id"
      @back="handleBack"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.shadow-decision-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
