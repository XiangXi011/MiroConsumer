<template>
  <section
    v-if="state"
    class="runtime-exceptional-state"
    :class="`runtime-exceptional-state--${state.severity}`"
    aria-live="polite"
  >
    <div class="runtime-state-copy">
      <span class="runtime-state-kicker">{{ state.kind }}</span>
      <strong>{{ state.title }}</strong>
      <p>{{ state.message }}</p>
    </div>
    <div class="runtime-state-action">
      <span>{{ state.recovery_action }}</span>
      <small v-if="state.next_retry_ms">retry {{ Math.round(state.next_retry_ms / 1000) }}s</small>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  state: {
    kind: string
    severity: 'info' | 'warning' | 'error'
    title: string
    message: string
    recovery_action: string
    next_retry_ms?: number
  } | null
}>()
</script>

<style scoped>
.runtime-exceptional-state {
  border: 1px solid #D6D3D1;
  background: #FFFCF5;
  color: #1F2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  margin: 12px 0;
}

.runtime-exceptional-state--error {
  border-color: #FCA5A5;
  background: #FFF1F2;
}

.runtime-exceptional-state--warning {
  border-color: #FCD34D;
  background: #FFFBEB;
}

.runtime-state-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.runtime-state-kicker {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #78716C;
}

.runtime-state-copy strong {
  font-size: 14px;
}

.runtime-state-copy p {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: #4B5563;
}

.runtime-state-action {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  font-size: 12px;
  color: #374151;
}

.runtime-state-action small {
  color: #78716C;
}

@media (max-width: 760px) {
  .runtime-exceptional-state {
    align-items: flex-start;
    flex-direction: column;
  }

  .runtime-state-action {
    align-items: flex-start;
  }
}
</style>
