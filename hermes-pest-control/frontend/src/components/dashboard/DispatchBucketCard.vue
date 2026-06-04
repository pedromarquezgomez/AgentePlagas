<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  buckets: { name: string; count: number; code: string }[]
}>()

const items = computed(() => {
  return props.buckets.map(b => {
    let bulletColor = 'bg-zinc'
    if (['URGENT_24H', 'urgent_24h'].includes(b.code)) bulletColor = 'bg-red'
    else if (['NEXT_48H', 'next_48h', 'THIS_WEEK', 'this_week'].includes(b.code)) bulletColor = 'bg-amber'
    return {
      ...b,
      bulletColor,
    }
  })
})
</script>

<template>
  <div class="dispatch-bucket-card">
    <h3 class="card-title">Distribución Dispatch Buckets</h3>
    <div class="bucket-list">
      <div v-for="item in items" :key="item.code" class="bucket-item">
        <div class="bucket-label-container">
          <span class="bullet-indicator" :class="item.bulletColor"></span>
          <span class="bucket-name">{{ item.name }}</span>
        </div>
        <span class="bucket-count">{{ item.count }} casos</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dispatch-bucket-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a;
  margin: 0 0 16px 0;
}

.bucket-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bucket-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  background: #09090b;
  border: 1px solid #27272a;
  font-size: 12px;
}

.bucket-label-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bullet-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bg-red {
  background: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.4);
}

.bg-amber {
  background: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);
}

.bg-zinc {
  background: #71717a;
}

.bucket-name {
  font-weight: 500;
  color: #d4d4d8;
}

.bucket-count {
  font-weight: 700;
  color: #f4f4f5;
  font-family: 'JetBrains Mono', monospace;
}
</style>
