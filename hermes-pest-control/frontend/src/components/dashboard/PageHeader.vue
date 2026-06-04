<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="page-header-band">
    <h2 class="page-title">{{ title }}</h2>
    <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
  </div>
</template>

<style scoped>
.page-header-band {
  border-bottom: 1px solid #18181b; /* zinc-900 */
  padding-bottom: 12px;
  text-align: left;
}

.page-title {
  font-size: 20px;
  font-weight: 800;
  color: #f4f4f5; /* zinc-100 */
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  color: #a1a1aa; /* zinc-400 */
  margin: 4px 0 0 0;
}
</style>
