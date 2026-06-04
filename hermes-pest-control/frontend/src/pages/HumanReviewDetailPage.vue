<script setup lang="ts">
import { useRouter } from 'vue-router'
import Breadcrumbs from '../components/dashboard/Breadcrumbs.vue'
import HumanReviewDetail from '../components/HumanReviewDetail.vue'

defineProps<{
  id: string
}>()

const router = useRouter()

function handleBack() {
  void router.push('/reviews')
}

function handleUnauthorized() {
  void router.push('/login')
}
</script>

<template>
  <div class="human-review-detail-page">
    <Breadcrumbs
      parentPath="/reviews"
      parentLabel="Revisión Humana"
      currentLabel="Detalle de Revisión"
    />

    <HumanReviewDetail
      :item-id="id"
      @back="handleBack"
      @unauthorized="handleUnauthorized"
    />
  </div>
</template>

<style scoped>
.human-review-detail-page {
  display: flex;
  flex-direction: column;
}
</style>
