<template>
  <router-view />
  <a
    class="source-link"
    href="https://github.com/miroconsumer/miroconsumer"
    target="_blank"
    rel="noopener noreferrer"
  >
    Source
  </a>
</template>

<script setup lang="ts">
// @ts-nocheck
// 使用 Vue Router 来管理页面
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #000000;
  background-color: #ffffff;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #000000;
}

::-webkit-scrollbar-thumb:hover {
  background: #333333;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

.source-link {
  position: fixed;
  right: 12px;
  bottom: 10px;
  z-index: 1000;
  color: #111111;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #111111;
  padding: 4px 8px;
  font-size: 12px;
  line-height: 1.2;
  text-decoration: none;
}

.source-link:focus,
.source-link:hover {
  background: #111111;
  color: #ffffff;
}
</style>
