<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import DocumentDetail from '../components/DocumentDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/documents')
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="document-detail-page">
    <Breadcrumbs
      parentPath="/documents"
      parentLabel="Documentos"
      currentLabel="Detalle de Documento"
    />

    <DocumentDetail
      :document-id="id"
      @back="handleBack"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.document-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
