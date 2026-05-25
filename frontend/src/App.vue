<template>
  <router-view />
</template>

<script setup lang="ts">
// @ts-nocheck
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: var(--mc-font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--mc-text-primary);
  background-color: var(--mc-bg-canvas);
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--mc-bg-subtle);
}

::-webkit-scrollbar-thumb {
  background: var(--mc-border-strong);
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--mc-accent);
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

</style>
