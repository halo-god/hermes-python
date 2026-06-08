<script setup lang="ts">
import { onMounted, ref } from "vue";
import Icon from "@/components/Icon.vue";
import ModalShell from "@/components/ModalShell.vue";
import { agentsApi, type Profile } from "@/api/agents";
import { conversationsApi } from "@/api/conversations";
import { useNotificationStore } from "@/stores/notifications";

const emit = defineEmits<{ close: []; created: [id: string] }>();
const ns = useNotificationStore();

const title = ref("");
const profiles = ref<Profile[]>([]);
const selectedAgents = ref<string[]>([]);
const loading = ref(false);

onMounted(async () => {
  try {
    profiles.value = await agentsApi.profiles();
  } catch { /* ignore */ }
});

function toggleAgent(id: string) {
  const idx = selectedAgents.value.indexOf(id);
  if (idx >= 0) selectedAgents.value.splice(idx, 1);
  else selectedAgents.value.push(id);
}

async function create() {
  if (!title.value.trim()) {
    ns.toast("请输入群聊名称", "warn");
    return;
  }
  if (!selectedAgents.value.length) {
    ns.toast("请至少选择一个AI助手", "warn");
    return;
  }
  loading.value = true;
  try {
    const agentIds = selectedAgents.value.map(
      (pid) => profiles.value.find((p) => p.id === pid)?.default_agent_id || pid
    );
    const res = await conversationsApi.createGroup(
      title.value.trim(),
      [], // no other human members for now
      agentIds,
    );
    emit("created", res.id);
  } catch (e: unknown) {
    ns.toast("创建失败：" + ((e as Error).message || "未知错误"), "error");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <ModalShell title="创建群聊" subtitle="选择AI助手组成群聊" :width="480" @close="emit('close')">
    <div style="padding: 0 4px">
      <div style="margin-bottom: 16px">
        <label style="font-size: 12px; color: var(--ink-mute); display: block; margin-bottom: 6px">群聊名称</label>
        <input
          v-model="title"
          class="group-input"
          placeholder="如：项目讨论组"
          @keydown.enter="create"
          autofocus
        />
      </div>

      <label style="font-size: 12px; color: var(--ink-mute); display: block; margin-bottom: 8px">
        选择AI助手 <span v-if="selectedAgents.length">({{ selectedAgents.length }} 已选)</span>
      </label>
      <div class="agent-grid">
        <button
          v-for="p in profiles.filter((pp) => pp.is_active)"
          :key="p.id"
          class="agent-card"
          :class="{ on: selectedAgents.includes(p.id) }"
          @click="toggleAgent(p.id)"
        >
          <span class="agent-avatar" :style="{ background: p.color }"><Icon :name="p.icon" /></span>
          <div class="agent-meta">
            <div class="agent-name">{{ p.name }}</div>
            <div class="agent-desc">{{ p.desc }}</div>
          </div>
          <Icon v-if="selectedAgents.includes(p.id)" name="check" class="agent-check" />
        </button>
      </div>
    </div>

    <template #foot>
      <button class="btn" @click="emit('close')">取消</button>
      <span style="flex: 1"></span>
      <button class="btn primary" :disabled="loading" @click="create">
        {{ loading ? '创建中...' : '创建群聊' }} <Icon v-if="!loading" name="arrow_up" :size="12" />
      </button>
    </template>
  </ModalShell>
</template>

<style scoped>
.group-input {
  width: 100%;
  padding: 8px 12px;
  border: 1.5px solid var(--rule);
  border-radius: 8px;
  background: var(--bg-panel);
  color: var(--ink);
  font-size: 13px;
  outline: none;
  transition: border-color 140ms;
}
.group-input:focus {
  border-color: var(--accent);
}
.agent-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
}
.agent-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1.5px solid var(--rule);
  background: var(--bg-panel);
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms, background 140ms;
  width: 100%;
}
.agent-card:hover {
  border-color: var(--accent-soft);
}
.agent-card.on {
  border-color: var(--accent);
  background: var(--accent-tint);
}
.agent-avatar {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}
.agent-meta { flex: 1; min-width: 0; }
.agent-name { font-size: 13px; font-weight: 600; color: var(--ink); }
.agent-desc { font-size: 11px; color: var(--ink-mute); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-check { color: var(--accent); flex-shrink: 0; }
</style>
