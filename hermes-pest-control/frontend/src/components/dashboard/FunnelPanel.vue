<script setup lang="ts">
defineProps<{
  funnelData: Array<{
    label: string
    value: number
    percent: number
    icon: string
  }>
}>()
</script>

<template>
  <div class="metrics-block col-span-2">
    <div>
      <h3 class="block-title">Embudo Operativo & Automatización</h3>
      <p class="block-subtitle">Conversión automatizada de interacciones conversacionales</p>
    </div>

    <div class="funnel-steps-list">
      <div v-for="step in funnelData" :key="step.label" class="funnel-step">
        <div class="funnel-step-meta">
          <span class="step-label-text">
            <svg v-if="step.icon === 'comments'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" /></svg>
            <svg v-else-if="step.icon === 'incidents'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
            <svg v-else-if="step.icon === 'proposed'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" /></svg>
            <svg v-else-if="step.icon === 'confirmed'" class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else class="step-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.746 3.746 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" /></svg>
            {{ step.label }}
          </span>
          <span class="step-value-text font-mono">{{ step.value }} ({{ step.percent }}%)</span>
        </div>
        <div class="step-bar-track">
          <div class="step-bar-fill" :style="{ width: step.percent + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metrics-block {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.col-span-2 {
  grid-column: span 2;
}

.block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #71717a;
  margin: 0;
}

.block-subtitle {
  font-size: 10px;
  color: #52525b;
  margin: 4px 0 0 0;
}

.funnel-steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.funnel-step {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.funnel-step-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  align-items: center;
}

.step-label-text {
  color: #d4d4d8;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-icon {
  width: 14px;
  height: 14px;
  color: #52525b;
}

.step-value-text {
  font-weight: 700;
  color: #f4f4f5;
}

.step-bar-track {
  background: #09090b;
  height: 8px;
  border-radius: 9999px;
  overflow: hidden;
}

.step-bar-fill {
  background: linear-gradient(90deg, #059669, #14b8a6); /* emerald-600 to teal-500 */
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease;
}
</style>
