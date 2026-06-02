<script setup lang="ts">
import ModalShell from "@/components/ModalShell.vue";
import Icon from "@/components/Icon.vue";
import { useChatStore } from "@/stores/chat";

const props = defineProps<{
  teamId: string;
  sharedAgentIds: string[];
}>();

const emit = defineEmits<{ close: []; toggle: [agentId: string] }>();
const chat = useChatStore();

function isShared(id: string) {
  return props.sharedAgentIds.includes(id);
}
</script>

<template>
  <ModalShell title="管理共享助手" subtitle="点击助手卡片以加入或移出团队共享" :width="560" @close="emit('close')">
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; max-height: 400px; overflow-y: auto">
      <button
        v-for="a in chat.agents"
        :key="a.id"
        class="agent-card"
        :style="isShared(a.id) ? 'border-color:var(--accent-soft);box-shadow:var(--shadow-sm);background:var(--accent-tint)' : ''"
        @click="emit('toggle', a.id)"
      >
        <div class="agent-icon" :style="{ background: a.color || '#b8852a' }">
          <Icon :name="a.icon || 'sparkle'" />
        </div>
        <div class="agent-meta">
          <div class="agent-name">
            {{ a.label }}
            <span v-if="isShared(a.id)" class="official">已共享</span>
          </div>
          <div class="agent-desc">{{ a.description }}</div>
        </div>
      </button>
    </div>
    <template #foot>
      <div style="display: flex; justify-content: flex-end; width: 100%">
        <button class="btn primary" @click="emit('close')">完成</button>
      </div>
    </template>
  </ModalShell>
</template>
