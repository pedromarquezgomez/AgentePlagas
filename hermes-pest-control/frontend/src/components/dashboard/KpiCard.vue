<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  description?: string
  iconType?: 'comments' | 'incidents' | 'conversion' | 'cost' | 'sla'
  progressValue?: number // 0 to 100
  variant?: 'default' | 'emerald' | 'indigo' | 'danger'
}>()

const iconSvg = computed(() => {
  switch (props.iconType) {
    case 'comments':
      return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon"><path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" /></svg>`
    case 'incidents':
      return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>`
    case 'conversion':
      return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
    case 'cost':
      return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.22.11a8.018 8.018 0 008.384-1.818M9 8.182L9.22 8.07a8.017 8.017 0 018.384 1.818M12 3m9 9a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
    case 'sla':
      return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
    default:
      return ''
  }
})

const valueColorClass = computed(() => {
  if (props.variant === 'emerald') return 'text-emerald'
  if (props.variant === 'indigo') return 'text-indigo'
  if (props.variant === 'danger') return 'text-danger'
  return 'text-default'
})
</script>

<template>
  <div class="kpi-card">
    <div class="kpi-header">
      <span class="kpi-title">{{ title }}</span>
      <span class="kpi-icon" v-html="iconSvg"></span>
    </div>
    <div class="kpi-body">
      <span class="kpi-value" :class="valueColorClass">{{ value }}</span>
      
      <!-- Option Progress Bar -->
      <div v-if="progressValue !== undefined" class="progress-bar-container">
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: progressValue + '%' }"></div>
        </div>
      </div>

      <p v-if="description" class="kpi-description">{{ description }}</p>
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 120px;
  transition: all 0.3s ease;
}

.kpi-card:hover {
  border-color: #3f3f46; /* zinc-700 */
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.kpi-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.kpi-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a; /* zinc-500 */
}

.kpi-icon :deep(.icon) {
  width: 18px;
  height: 18px;
  color: #3f3f46; /* zinc-700 */
}

.kpi-value {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.text-default {
  color: #f4f4f5; /* zinc-100 */
}

.text-emerald {
  color: #34d399; /* emerald-400 */
}

.text-indigo {
  color: #818cf8; /* indigo-400 */
}

.text-danger {
  color: #f87171; /* red-400 */
}

.progress-bar-container {
  margin-top: 8px;
  width: 100%;
}

.progress-bar-track {
  background: #09090b; /* zinc-950 */
  height: 6px;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar-fill {
  background: #10b981; /* emerald-500 */
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease-out;
}

.kpi-description {
  font-size: 10px;
  color: #a1a1aa; /* zinc-400 */
  margin: 6px 0 0 0;
}
</style>
