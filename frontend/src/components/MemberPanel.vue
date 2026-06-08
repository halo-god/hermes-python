<script setup lang="ts">
/* Collapsible member panel for group chats — shows AI agents + human members */
import { ref, computed, onMounted, watch } from 'vue';
import Icon from '@/components/Icon.vue';
import { conversationsApi } from '@/api/conversations';
import { agentsApi, type Profile } from '@/api/agents';
import type { GroupMember } from '@/types';

const props = defineProps<{
  conversationId: string;
  agents: { agent_id: string; name: string; color: string; icon: string }[];
}>();

const emit = defineEmits<{ close: [] }>();

const members = ref<GroupMember[]>([]);
const profiles = ref<Profile[]>([]);
const loading = ref(false);

const humanMembers = computed(() => members.value.filter((m) => m.user_id));
const aiMembers = computed(() => {
  // Combine agents from props with any agent members from the API
  const fromProps = props.agents.map((a) => ({
    id: a.agent_id,
    name: a.name,
    color: a.color,
    icon: a.icon,
    isFromProps: true,
  }));
  return fromProps;
});

async function load() {
  loading.value = true;
  try {
    const [mem, prof] = await Promise.all([
      conversationsApi.getMembers(props.conversationId),
      agentsApi.profiles().catch(() => []),
    ]);
    members.value = mem;
    profiles.value = prof;
  } catch {
    /* ignore */
  } finally {
    loading.value = false;
  }
}

function getProfileForAgent(agentId: string) {
  return profiles.value.find((p) => p.default_agent_id === agentId);
}

onMounted(load);
watch(() => props.conversationId, load);
</script>

<template>
  <div class="member-panel">
    <div class="mp-header">
      <span class="mp-title">成员</span>
      <button class="mp-close" @click="emit('close')"><Icon name="close" :size="14" /></button>
    </div>

    <div v-if="loading" class="mp-empty">加载中…</div>

    <template v-else>
      <!-- AI Agents -->
      <div class="mp-section">
        <div class="mp-label"><Icon name="sparkle" :size="12" /> AI 助手</div>
        <div v-for="a in aiMembers" :key="a.id" class="mp-item">
          <div class="mp-avatar" :style="{ background: a.color || '#b8852a' }">
            <Icon :name="a.icon || 'sparkle'" :size="14" />
          </div>
          <div class="mp-info">
            <div class="mp-name">{{ a.name }}</div>
            <div class="mp-sub">{{ getProfileForAgent(a.id)?.desc || 'AI 助手' }}</div>
          </div>
        </div>
        <div v-if="!aiMembers.length" class="mp-empty-sm">暂无 AI 助手</div>
      </div>

      <!-- Human Members -->
      <div class="mp-section">
        <div class="mp-label"><Icon name="user" :size="12" /> 成员</div>
        <div v-for="m in humanMembers" :key="m.id" class="mp-item">
          <div class="mp-avatar mp-avatar-human">
            {{ (m.user_id || '?')[0]?.toUpperCase() }}
          </div>
          <div class="mp-info">
            <div class="mp-name">{{ m.user_id || '未知用户' }}</div>
            <div class="mp-sub">{{ m.role === 'admin' ? '管理员' : '成员' }}</div>
          </div>
        </div>
        <div v-if="!humanMembers.length" class="mp-empty-sm">暂无其他成员</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.member-panel {
  width: 220px;
  flex-shrink: 0;
  border-left: 1px solid var(--rule);
  background: var(--bg-panel);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.mp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--rule-soft);
}
.mp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
.mp-close {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: var(--ink-mute);
}
.mp-close:hover { background: rgba(29,26,20,0.06); color: var(--ink); }
.mp-section {
  padding: 10px 14px;
}
.mp-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-mute);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.mp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}
.mp-avatar {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  color: white;
  flex-shrink: 0;
}
.mp-avatar-human {
  background: var(--ink-mute);
  font-size: 12px;
  font-weight: 600;
}
.mp-info {
  flex: 1;
  min-width: 0;
}
.mp-name {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mp-sub {
  font-size: 11px;
  color: var(--ink-mute);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mp-empty, .mp-empty-sm {
  color: var(--ink-mute);
  font-size: 12px;
  text-align: center;
}
.mp-empty { padding: 24px 0; }
.mp-empty-sm { padding: 8px 0; font-size: 11px; }
</style>
