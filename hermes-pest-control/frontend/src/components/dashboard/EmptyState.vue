<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>

<template>
  <div class="empty-state-container">
    <div class="empty-icon-wrapper">
      <svg class="empty-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
      </svg>
    </div>
    <p class="empty-message">{{ message }}</p>
  </div>
</template>

<style scoped>
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: #09090b; /* zinc-950 */
  border: 1px dashed #27272a; /* zinc-800 */
  border-radius: 8px;
  text-align: center;
  max-width: 600px;
  margin: 20px auto;
}

.empty-icon-wrapper {
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a;
  border-radius: 50%;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.empty-icon {
  width: 24px;
  height: 24px;
  color: #71717a; /* zinc-500 */
}

.empty-message {
  font-size: 13px;
  color: #a1a1aa; /* zinc-400 */
  margin: 0;
  font-weight: 500;
}
</style>
