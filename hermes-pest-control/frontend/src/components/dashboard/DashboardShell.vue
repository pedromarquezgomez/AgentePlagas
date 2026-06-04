<script setup lang="ts">
import SidebarNav from './SidebarNav.vue'
import TopFiltersBar from './TopFiltersBar.vue'
import ToastContainer, { Toast } from './ToastContainer.vue'

defineProps<{
  currentPath: string
  activeIncidentsCount?: number
  isLoading: boolean
  lastUpdated: string
  channel: string
  pestType: string
  priority: string
  toasts: Toast[]
}>()

const emit = defineEmits<{
  (e: 'navigate', path: string): void
  (e: 'refresh'): void
  (e: 'update:channel', val: string): void
  (e: 'update:pestType', val: string): void
  (e: 'update:priority', val: string): void
}>()
</script>

<template>
  <div class="dashboard-shell">
    <!-- Top Filter & Navigation Bar -->
    <TopFiltersBar 
      :channel="channel"
      :pestType="pestType"
      :priority="priority"
      :isLoading="isLoading"
      :lastUpdated="lastUpdated"
      @update:channel="emit('update:channel', $event)"
      @update:pestType="emit('update:pestType', $event)"
      @update:priority="emit('update:priority', $event)"
      @refresh="emit('refresh')"
    />

    <!-- Main Shell Body (Sidebar + Content Workspace) -->
    <div class="shell-body">
      <!-- Sidebar Nav -->
      <SidebarNav 
        :currentPath="currentPath"
        :activeIncidentsCount="activeIncidentsCount"
        @navigate="emit('navigate', $event)"
      />

      <!-- Scrollable Main Workspace -->
      <main class="main-workspace">
        <slot></slot>
      </main>
    </div>

    <!-- Toast Notifications Layer -->
    <ToastContainer :toasts="toasts" />
  </div>
</template>

<style scoped>
.dashboard-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #09090b; /* zinc-950 */
  color: #f4f4f5; /* zinc-100 */
  overflow: hidden;
  font-family: 'Inter', sans-serif;
}

.shell-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main-workspace {
  flex: 1;
  overflow-y: auto;
  background: #09090b;
  padding: 24px;
}

/* Custom Scrollbar */
.main-workspace::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.main-workspace::-webkit-scrollbar-track {
  background: #09090b;
}

.main-workspace::-webkit-scrollbar-thumb {
  background: #27272a;
  border-radius: 3px;
}

.main-workspace::-webkit-scrollbar-thumb:hover {
  background: #3f3f46;
}
</style>
