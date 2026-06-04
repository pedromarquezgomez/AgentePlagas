<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  payload: any
  title: string
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const copySuccess = ref(false)

const prettyJson = computed(() => {
  if (!props.payload) return ''
  return JSON.stringify(props.payload, null, 2)
})

// Extract structured audit/tool fields if present
const structuredFields = computed(() => {
  if (!props.payload) return null
  
  const p = props.payload
  const fields: Record<string, any> = {}
  
  if (p.tool_input || p.metadata?.tool_input) {
    fields['Input de Herramienta (tool_input)'] = p.tool_input || p.metadata?.tool_input
  }
  if (p.tool_output || p.metadata?.tool_output || p.execution_result) {
    fields['Output de Ejecución (tool_output)'] = p.tool_output || p.metadata?.tool_output || p.execution_result
  }
  if (p.approved_payload) {
    fields['Payload Aprobado (approved_payload)'] = p.approved_payload
  }
  if (p.metadata || p.audit_metadata) {
    fields['Metadata de Auditoría (audit_metadata)'] = p.metadata || p.audit_metadata
  }
  
  return Object.keys(fields).length > 0 ? fields : null
})

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(prettyJson.value)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  } catch (err) {
    console.error('Error al copiar al portapapeles:', err)
  }
}
</script>

<template>
  <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
    <div class="drawer-container">
      <div class="drawer-header">
        <h4 class="drawer-title">Auditoría: {{ title }}</h4>
        <button class="close-icon-btn" @click="emit('close')">
          <svg class="close-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="drawer-body">
        <!-- Render structured sections if available -->
        <div v-if="structuredFields" class="structured-sections">
          <div v-for="(val, label) in structuredFields" :key="label" class="structured-card">
            <span class="structured-label font-mono">{{ label }}</span>
            <pre class="json-code"><code>{{ JSON.stringify(val, null, 2) }}</code></pre>
          </div>
        </div>

        <!-- Otherwise show full raw JSON -->
        <div v-else>
          <pre class="json-code"><code>{{ prettyJson }}</code></pre>
        </div>
      </div>
      
      <div class="drawer-footer">
        <button class="footer-copy-btn" @click="copyToClipboard">
          <svg v-if="copySuccess" class="copy-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
          <svg v-else class="copy-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H5.25m11.9-3.664A2.251 2.251 0 0015 2.25h-3a2.25 2.25 0 00-1.85.908m7.75 0a2.25 2.25 0 01.529 1.256c.018.22.027.443.027.668V7.5a.75.75 0 01-.75.75h-10.5a.75.75 0 01-.75-.75V5.074c0-.225.009-.448.027-.668a2.25 2.25 0 01.528-1.256m11.9 0a2.25 2.25 0 00-1.75-.856h-1.5a2.25 2.25 0 00-1.75.856m7.75 0a2.251 2.251 0 01-.25 1.341c-.085.15-.224.275-.389.349a2.25 2.25 0 01-.908.188h-5.25a2.25 2.25 0 01-.908-.188c-.165-.074-.304-.2-.389-.35a2.251 2.251 0 01-.25-1.34" />
          </svg>
          {{ copySuccess ? 'Copiado' : 'Copiar JSON' }}
        </button>
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
  max-width: 38rem; /* max-w-2xl */
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 600px;
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

.structured-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.structured-card {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.structured-label {
  font-size: 10px;
  font-weight: 700;
  color: #71717a;
  text-transform: uppercase;
  border-bottom: 1px solid #27272a;
  padding-bottom: 4px;
  text-align: left;
}

.json-code {
  margin: 0;
  color: #34d399; /* emerald-400 */
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  line-height: 1.5;
  text-align: left;
  overflow-x: auto;
}

.drawer-footer {
  padding: 16px;
  border-top: 1px solid #27272a;
  background: #18181b;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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

.footer-copy-btn {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.footer-copy-btn:hover {
  background: #0284c7;
  color: #09090b;
  border-color: #0284c7;
}

.copy-icon {
  width: 14px;
  height: 14px;
}
</style>
