<script setup lang="ts">
/* Notification bell dropdown — shows inbox from notifications store. */
import { computed, ref, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/Icon.vue";
import { useNotificationStore } from "@/stores/notifications";
import { useChatStore } from "@/stores/chat";

const ns = useNotificationStore();
const router = useRouter();
const chat = useChatStore();
const open = ref(false);
const wrap = ref<HTMLElement | null>(null);

function toggle() { open.value = !open.value; }
function onDoc(e: MouseEvent) {
  if (wrap.value && !wrap.value.contains(e.target as Node)) open.value = false;
}
onMounted(() => document.addEventListener("mousedown", onDoc));
onBeforeUnmount(() => document.removeEventListener("mousedown", onDoc));

async function onNotifClick(n: { id: number; link?: string }) {
  ns.markRead(n.id);
  if (n.link) {
    // Parse ?c=conversationId from link
    const match = n.link.match(/[?&]c=([^&]+)/);
    if (match) {
      const cid = match[1];
      await chat.openConversation(cid);
      router.push("/");
    } else {
      router.push(n.link);
    }
    open.value = false;
  }
}

const unread = computed(() => ns.unreadCount());
const KIND_ICON: Record<string, string> = { info: "sparkle", success: "check", warn: "bolt", error: "close" };
const KIND_COLOR: Record<string, string> = {
  info: "var(--accent)",
  success: "var(--ok)",
  warn: "#d4821a",
  error: "var(--danger)",
};

function relTime(ts: string) {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}
</script>

<template>
  <div ref="wrap" style="position: relative">
    <button
      class="icon-btn notif-bell"
      :class="{ 'has-unread': unread > 0 }"
      title="通知"
      @click="toggle"
    >
      <Icon name="bolt" :size="16" />
      <span v-if="unread > 0" class="notif-badge">{{ unread > 9 ? "9+" : unread }}</span>
    </button>

    <Transition name="panel-drop">
      <div v-if="open" class="notif-panel">
        <div class="notif-header">
          <span class="notif-title">通知</span>
          <span class="notif-count" v-if="ns.inbox.length">{{ ns.inbox.length }} 条</span>
          <button v-if="unread > 0" class="notif-mark-all" @click="ns.markAllRead">全部已读</button>
        </div>

        <div class="notif-list" v-if="ns.inbox.length">
          <div
            v-for="n in ns.inbox"
            :key="n.id"
            class="notif-item"
            :class="{ unread: !n.read, 'has-link': !!n.link }"
            @click="onNotifClick(n)"
          >
            <span class="notif-kind-icon" :style="{ color: KIND_COLOR[n.kind] }">
              <Icon :name="KIND_ICON[n.kind] || 'sparkle'" :size="14" />
            </span>
            <div class="notif-body">
              <div class="notif-item-title">{{ n.title }}</div>
              <div class="notif-item-body">{{ n.body }}</div>
              <div class="notif-item-ts">{{ relTime(n.ts) }}</div>
            </div>
            <button class="notif-rm" @click.stop="ns.remove(n.id)" title="移除">×</button>
          </div>
        </div>

        <div v-else class="notif-empty">
          <Icon name="check" :size="20" style="color: var(--ink-faint)" />
          <div style="margin-top: 8px">暂无通知</div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notif-bell { position: relative }
.notif-badge {
  position: absolute;
  top: 2px; right: 2px;
  background: var(--danger);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  padding: 1px 3px;
  border-radius: 999px;
  min-width: 14px;
  text-align: center;
}
.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 340px;
  background: var(--bg-panel);
  border: 1px solid var(--rule);
  border-radius: 14px;
  box-shadow: var(--shadow-lg);
  z-index: 800;
  overflow: hidden;
}
.notif-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px 10px;
  border-bottom: 1px solid var(--rule);
}
.notif-title { font-weight: 600; font-size: 13.5px; color: var(--ink); flex: 1 }
.notif-count { font-size: 11.5px; color: var(--ink-mute) }
.notif-mark-all {
  font-size: 11.5px;
  color: var(--accent-deep);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.notif-mark-all:hover { text-decoration: underline }
.notif-list { max-height: 360px; overflow-y: auto }
.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  transition: background 120ms;
}
.notif-item:last-child { border-bottom: none }
.notif-item:hover { background: rgba(29, 26, 20, 0.04) }
.notif-item.has-link { cursor: pointer }
.notif-item.has-link:hover { background: rgba(184, 133, 42, 0.08) }
.notif-item.unread { background: var(--accent-tint) }
.notif-item.unread:hover { background: color-mix(in srgb, var(--accent-tint) 85%, var(--rule)) }
.notif-kind-icon { flex-shrink: 0; padding-top: 1px }
.notif-body { flex: 1; min-width: 0 }
.notif-item-title { font-size: 12.5px; font-weight: 600; color: var(--ink) }
.notif-item-body { font-size: 11.5px; color: var(--ink-soft); margin-top: 2px; line-height: 1.4 }
.notif-item-ts { font-size: 11px; color: var(--ink-faint); margin-top: 4px }
.notif-rm {
  color: var(--ink-faint);
  font-size: 15px;
  padding: 0 4px;
  background: none;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  line-height: 1;
}
.notif-rm:hover { color: var(--ink-mute) }
.notif-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--ink-mute);
  font-size: 12.5px;
}

.panel-drop-enter-active, .panel-drop-leave-active { transition: opacity 150ms, transform 150ms }
.panel-drop-enter-from, .panel-drop-leave-to { opacity: 0; transform: translateY(-8px) }
</style>
