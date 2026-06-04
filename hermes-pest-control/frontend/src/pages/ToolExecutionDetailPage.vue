<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import ToolExecutionDetail from '../components/ToolExecutionDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/tools')
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="tool-execution-detail-page">
    <Breadcrumbs
      parentPath="/tools"
      parentLabel="Acciones de la IA"
      currentLabel="Detalle de Acción"
    />

    <ToolExecutionDetail
      :execution-id="id"
      @back="handleBack"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.tool-execution-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
