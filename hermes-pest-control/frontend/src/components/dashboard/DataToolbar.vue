<template>
  <div class="data-toolbar">
    <div class="toolbar-left">
      <slot name="left"></slot>
    </div>
    <div class="toolbar-right">
      <slot name="right"></slot>
    </div>
  </div>
</template>

<style scoped>
.data-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #18181b; /* zinc-900 */
  border: 1px solid #27272a; /* zinc-800 */
  border-radius: 8px;
  padding: 12px 16px;
  align-items: stretch;
}

@media (min-width: 768px) {
  .data-toolbar {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.toolbar-left,
.toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  justify-content: flex-end;
}
</style>
