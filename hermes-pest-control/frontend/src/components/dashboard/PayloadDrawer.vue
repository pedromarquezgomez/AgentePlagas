<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  payload: any
  title: string
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const prettyJson = computed(() => {
  if (!props.payload) return ''
  return JSON.stringify(props.payload, null, 2)
})
</script>

<template>
  <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
    <div class="drawer-container">
      <div class="drawer-header">
        <h4 class="drawer-title">Payload: {{ title }}</h4>
        <button class="close-icon-btn" @click="emit('close')">
          <svg class="close-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="drawer-body">
        <pre class="json-code"><code>{{ prettyJson }}</code></pre>
      </div>
      
      <div class="drawer-footer">
        <button class="footer-close-btn" @click="emit('close')">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 16px;
  backdrop-filter: blur(4px);
}

.drawer-container {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  max-width: 32rem; /* max-w-lg */
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 500px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.drawer-header {
  padding: 16px;
  border-bottom: 1px solid #27272a;
  background: #09090b; /* zinc-950 */
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #34d399; /* emerald-400 */
  font-family: 'JetBrains Mono', monospace;
  margin: 0;
}

.close-icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #71717a;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-icon-btn:hover {
  color: #f4f4f5;
  background: #27272a;
}

.close-icon {
  width: 18px;
  height: 18px;
}

.drawer-body {
  flex: 1;
  padding: 16px;
  overflow: auto;
  background: #09090b;
}

.json-code {
  margin: 0;
  color: #34d399; /* emerald-400 */
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  text-align: left;
}

.drawer-footer {
  padding: 16px;
  border-top: 1px solid #27272a;
  background: #18181b;
  display: flex;
  justify-content: flex-end;
}

.footer-close-btn {
  background: #27272a;
  border: 1px solid #3f3f46;
  color: #f4f4f5;
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.footer-close-btn:hover {
  background: #3f3f46;
  border-color: #52525b;
}
</style>
