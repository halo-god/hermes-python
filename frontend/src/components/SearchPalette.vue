<script setup lang="ts">
/* 1:1 port of the prototype ⌘K search palette — searches conversations + agents. */
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/Icon.vue";
import { useChatStore } from "@/stores/chat";

const emit = defineEmits<{ close: [] }>();
const chat = useChatStore();
const router = useRouter();
const q = ref("");
const input = ref<HTMLInputElement | null>(null);

onMounted(() => nextTick(() => input.value?.focus()));

const matches = computed(() => {
  const term = q.value.trim().toLowerCase();
  if (!term) {
    return { convos: chat.conversations.slice(0, 5), agents: chat.agents.slice(0, 4) };
  }
  return {
    convos: chat.conversations.filter((c) => c.title.toLowerCase().includes(term)),
    agents: chat.agents.filter((a) => a.label.toLowerCase().includes(term) || (a.description || "").toLowerCase().includes(term)),
  };
});

async function openConvo(id: string) {
  emit("close");
  await chat.openConversation(id);
  router.push({ path: "/", query: { c: id } });
}
function pickAgent() {
  emit("close");
  router.push("/");
}
</script>

<template>
  <div class="scrim" @mousedown.self="emit('close')">
    <div class="palette" @keydown.esc="emit('close')">
      <input ref="input" v-model="q" class="palette-input" placeholder="搜索对话、助手…  按 Esc 关闭" @keydown.esc="emit('close')" />
      <div class="palette-list">
        <template v-if="matches.convos.length">
          <div class="palette-section">对话</div>
          <button v-for="c in matches.convos" :key="c.id" class="menu-item" @click="openConvo(c.id)">
            <Icon :name="c.icon || 'chat'" />
            <span class="m-name">{{ c.title }}</span>
            <span class="m-tag">{{ c.pinned ? "已置顶" : "" }}</span>
          </button>
        </template>
        <template v-if="matches.agents.length">
          <div class="palette-section">助手</div>
          <button v-for="a in matches.agents" :key="a.id" class="menu-item" @click="pickAgent">
            <Icon :name="a.icon || 'sparkle'" :style="{ color: a.color || '#b8852a' }" />
            <span class="m-name">{{ a.label }}</span>
            <span class="m-tag">{{ a.kind === "builtin_mock" ? "mock" : "acp" }}</span>
          </button>
        </template>
        <div v-if="!matches.convos.length && !matches.agents.length" class="palette-empty">没有匹配项</div>
      </div>
    </div>
  </div>
</template>
