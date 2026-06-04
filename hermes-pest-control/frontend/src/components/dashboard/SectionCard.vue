<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  subtitle?: string
  colSpan?: number
}>(), {
  colSpan: 1
})

const cardClass = computed(() => {
  return {
    'metrics-block': true,
    'col-span-2': props.colSpan === 2
  }
})
</script>

<template>
  <div :class="cardClass">
    <div v-if="title || subtitle" class="card-header-band">
      <h3 v-if="title" class="block-title">{{ title }}</h3>
      <p v-if="subtitle" class="block-subtitle">{{ subtitle }}</p>
    </div>
    <div class="card-body-content">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.metrics-block {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.col-span-2 {
  grid-column: span 2;
}

.card-header-band {
  margin-bottom: 16px;
}

.block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a; /* zinc-500 */
  margin: 0;
}

.block-subtitle {
  font-size: 10px;
  color: #52525b; /* zinc-600 */
  margin: 4px 0 0 0;
}

.card-body-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
