<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  parentPath: string
  parentLabel: string
  currentLabel: string
}>()

const router = useRouter()

function navigateTo(path: string) {
  void router.push(path)
}
</script>

<template>
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <button 
      class="breadcrumb-link" 
      type="button" 
      @click="navigateTo(parentPath)"
    >
      {{ parentLabel }}
    </button>
    <span class="breadcrumb-separator">
      <!-- Chevron right icon -->
      <svg class="separator-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
      </svg>
    </span>
    <span class="breadcrumb-current">{{ currentLabel }}</span>
  </nav>
</template>

<style scoped>
.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #71717a; /* zinc-500 */
  margin-bottom: 16px;
}

.breadcrumb-link {
  background: transparent;
  border: none;
  padding: 0;
  color: #34d399; /* emerald-400 */
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
  outline: none;
}

.breadcrumb-link:hover {
  color: #10b981; /* emerald-500 */
  text-decoration: underline;
}

.breadcrumb-separator {
  display: flex;
  align-items: center;
}

.separator-icon {
  width: 10px;
  height: 10px;
  color: #3f3f46; /* zinc-700 */
}

.breadcrumb-current {
  color: #f4f4f5; /* zinc-100 */
  font-weight: 500;
}
</style>
