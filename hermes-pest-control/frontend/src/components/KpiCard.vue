<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title: string
    value: string | number
    description?: string
    variant?: 'default' | 'danger' | 'warning' | 'success'
  }>(),
  {
    variant: 'default',
  }
)

const cardStyles = computed(() => {
  switch (props.variant) {
    case 'danger':
      return {
        background: '#fff5f5',
        border: '1px solid #feb2b2',
        color: '#9b2c2c',
      }
    case 'warning':
      return {
        background: '#fffaf0',
        border: '1px solid #fbd38d',
        color: '#dd6b20',
      }
    case 'success':
      return {
        background: '#f0fff4',
        border: '1px solid #9ae6b4',
        color: '#22543d',
      }
    default:
      return {
        background: '#ffffff',
        border: '1px solid #d8dee5',
        color: '#17202a',
      }
  }
})

const titleColor = computed(() => {
  if (props.variant === 'default') return '#405060'
  return 'inherit'
})

const valueColor = computed(() => {
  if (props.variant === 'default') return '#235b8c'
  return 'inherit'
})
</script>

<template>
  <div 
    class="metricCard" 
    :style="[cardStyles, { minHeight: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', transition: 'all 0.2s ease-in-out' }]"
  >
    <div>
      <span 
        class="metricTitle" 
        :style="{ color: titleColor, display: 'block', textTransform: 'uppercase', fontSize: '12px', fontWeight: '800', letterSpacing: '0.05em' }"
      >
        {{ title }}
      </span>
      <span 
        class="metricValue" 
        :style="{ color: valueColor, fontSize: '32px', fontWeight: '900', display: 'block', marginTop: '6px' }"
      >
        {{ value }}
      </span>
    </div>
    <div 
      v-if="description" 
      style="font-size: 13px; font-weight: 700; margin-top: 10px; color: inherit; opacity: 0.85;"
    >
      {{ description }}
    </div>
  </div>
</template>

<style scoped>
.metricCard:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
</style>
