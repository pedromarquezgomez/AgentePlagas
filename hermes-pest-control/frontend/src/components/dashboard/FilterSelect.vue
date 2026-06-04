<script setup lang="ts">
defineProps<{
  modelValue: string
  options: Array<{ value: string; label: string }>
  label?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
}>()
</script>

<template>
  <div class="filter-group">
    <label v-if="label" class="filter-label">{{ label }}</label>
    <select 
      :value="modelValue" 
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      class="filter-select"
    >
      <option v-for="opt in options" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #71717a; /* zinc-500 */
  letter-spacing: 0.05em;
}

.filter-select {
  background: #09090b; /* zinc-950 */
  border: 1px solid #27272a; /* zinc-800 */
  color: #e4e4e7; /* zinc-200 */
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  outline: none;
}

.filter-select:hover {
  border-color: #3f3f46; /* zinc-700 */
}

.filter-select:focus {
  border-color: #10b981; /* emerald-500 */
}
</style>
