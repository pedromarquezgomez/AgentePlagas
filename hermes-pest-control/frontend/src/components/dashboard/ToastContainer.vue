<script setup lang="ts">
export interface Toast {
  id: number
  title: string
  message: string
  type: 'success' | 'error'
}

defineProps<{
  toasts: Toast[]
}>()
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast-list">
      <div 
        v-for="toast in toasts" 
        :key="toast.id" 
        class="toast-card"
        :class="toast.type === 'success' ? 'toast-success' : 'toast-error'"
      >
        <!-- Success Icon -->
        <svg v-if="toast.type === 'success'" class="toast-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        
        <!-- Error Icon -->
        <svg v-else class="toast-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>

        <div class="toast-content">
          <h5 class="toast-title">{{ toast.title }}</h5>
          <p class="toast-message">{{ toast.message }}</p>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 9999;
  pointer-events: none;
}

.toast-card {
  pointer-events: auto;
  display: flex;
  align-items: start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  width: 320px;
  border: 1px solid transparent;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
}

.toast-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.toast-content {
  display: flex;
  flex-direction: column;
}

.toast-title {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

.toast-message {
  font-size: 11px;
  margin: 4px 0 0 0;
  line-height: 1.4;
  opacity: 0.9;
}

/* Success Styles */
.toast-success {
  background: rgba(6, 78, 59, 0.9); /* green-900 / emerald-900 */
  border-color: rgba(16, 185, 129, 0.3);
  color: #d1fae5;
}
.toast-success .toast-icon {
  color: #34d399; /* emerald-400 */
}

/* Error Styles */
.toast-error {
  background: rgba(127, 29, 29, 0.9); /* red-900 */
  border-color: rgba(239, 68, 68, 0.3);
  color: #fee2e2;
}
.toast-error .toast-icon {
  color: #f87171; /* red-400 */
}

/* Transition Animations */
.toast-list-enter-active {
  transition: all 0.3s ease-out;
}
.toast-list-leave-active {
  transition: all 0.2s ease-in;
}
.toast-list-enter-from {
  opacity: 0;
  transform: translateX(30px) translateY(10px);
}
.toast-list-leave-to {
  opacity: 0;
  transform: translateX(50px);
}
</style>
