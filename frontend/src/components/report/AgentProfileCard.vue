<template>
  <div class="agent-profile-card">
    <div class="profile-card-header">
      <div class="profile-card-avatar">{{ (agent.username || 'A')[0] }}</div>
      <div class="profile-card-info">
        <div class="profile-card-name">{{ agent.username }}</div>
        <div class="profile-card-meta">
          <span v-if="agent.name" class="profile-card-handle">@{{ agent.name }}</span>
          <span class="profile-card-profession">{{ agent.profession || t('step2.unknownProfession') }}</span>
        </div>
      </div>
      <button class="profile-card-toggle" @click="showFullProfile = !showFullProfile">
        <svg
          :class="{ 'is-expanded': showFullProfile }"
          viewBox="0 0 24 24"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
    <div v-if="showFullProfile && agent.bio" class="profile-card-body">
      <div class="profile-card-bio">
        <div class="profile-card-label">{{ t('step5.profileBio') }}</div>
        <p>{{ agent.bio }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// @ts-nocheck
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps({
  agent: { type: Object, required: true },
})

const { t } = useI18n()

const showFullProfile = ref(true)
</script>

<style scoped>
.agent-profile-card {
  border-bottom: 1px solid #E5E7EB;
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
}

.profile-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
}

.profile-card-avatar {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  background: linear-gradient(135deg, #1F2937 0%, #374151 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.2);
}

.profile-card-info {
  flex: 1;
  min-width: 0;
}

.profile-card-name {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 2px;
}

.profile-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6B7280;
}

.profile-card-handle {
  color: #9CA3AF;
}

.profile-card-profession {
  padding: 2px 8px;
  background: #E5E7EB;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.profile-card-toggle {
  width: 28px;
  height: 28px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.profile-card-toggle:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}

.profile-card-toggle svg {
  transition: transform 0.3s ease;
}

.profile-card-toggle svg.is-expanded {
  transform: rotate(180deg);
}

.profile-card-body {
  padding: 0 20px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-card-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

.profile-card-bio {
  background: #FFFFFF;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
}

.profile-card-bio p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4B5563;
}
</style>
