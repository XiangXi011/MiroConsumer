<template>
  <div class="rep-card">
    <div class="rep-card-header">
      <span class="rep-role">{{ roleLabel }}</span>
      <span class="rep-segment">{{ segment }}</span>
    </div>
    <div class="rep-card-body">
      <div class="rep-field">
        <span class="rep-key">Channel</span>
        <span class="rep-value">{{ channelLabel }}</span>
      </div>
      <div class="rep-field">
        <span class="rep-key">Quote</span>
        <span class="rep-value rep-quote">"{{ keyQuote }}"</span>
      </div>
      <div class="rep-field">
        <span class="rep-key">Attitude</span>
        <span class="rep-value">{{ attitudeText }}</span>
      </div>
      <div class="rep-field">
        <span class="rep-key">Purchase Intent</span>
        <span class="rep-value mono">{{ purchaseIntentDeltaText }}</span>
      </div>
      <div class="rep-field">
        <span class="rep-key">Influence</span>
        <span class="rep-value mono">{{ influenceText }}</span>
      </div>
    </div>
    <div class="rep-card-footer">
      <button class="rep-ask-btn" @click="$emit('ask')">Ask Consumer</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  roleLabel: { type: String, default: '' },
  segment: { type: String, default: '' },
  channelLabel: { type: String, default: '' },
  keyQuote: { type: String, default: '' },
  attitudeText: { type: String, default: '' },
  purchaseIntentDeltaText: { type: String, default: '' },
  influenceText: { type: String, default: '' },
})

defineEmits(['ask'])
</script>

<style scoped>
.rep-card {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rep-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.rep-role {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.rep-segment {
  font-size: 11px;
  color: #6B7280;
}

.rep-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rep-field {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.rep-key {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7280;
  min-width: 90px;
}

.rep-value {
  font-size: 12px;
  color: #374151;
  text-align: right;
}

.rep-quote {
  font-style: italic;
  color: #4B5563;
}

.rep-card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

.rep-ask-btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #FFFFFF;
  background: #1F2937;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.rep-ask-btn:hover {
  background: #374151;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}
</style>
