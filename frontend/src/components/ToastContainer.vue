<script setup lang="ts">
/* Global toast container — mount once in App.vue.
   Reads from the notifications store; replaces all ad-hoc DOM toast hacks. */
import { useNotificationStore } from "@/stores/notifications";
import Icon from "@/components/Icon.vue";

const ns = useNotificationStore();

const KIND_ICON: Record<string, string> = {
  ok: "check",
  error: "close",
  warn: "bolt",
  info: "sparkle",
};
const KIND_COLOR: Record<string, string> = {
  ok: "var(--accent)",
  error: "var(--danger)",
  warn: "#d4821a",
  info: "var(--accent-deep)",
};
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in ns.toasts" :key="t.id" class="toast-item" :style="{ '--tc': KIND_COLOR[t.kind] }">
          <span class="toast-icon"><Icon :name="KIND_ICON[t.kind] || 'check'" :size="13" /></span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click="ns.dismiss(t.id)">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 9999;
  pointer-events: none;
}
.toast-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-panel);
  border: 1px solid var(--rule);
  box-shadow: var(--shadow-md);
  border-radius: 12px;
  padding: 9px 14px 9px 12px;
  font-size: 13px;
  color: var(--ink);
  pointer-events: all;
  min-width: 220px;
  max-width: 380px;
}
.toast-icon {
  display: flex;
  align-items: center;
  color: var(--tc);
  flex-shrink: 0;
}
.toast-msg { flex: 1 }
.toast-close {
  color: var(--ink-mute);
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
  cursor: pointer;
  background: none;
  border: none;
}
.toast-close:hover { color: var(--ink) }

.toast-enter-active, .toast-leave-active { transition: opacity 200ms, transform 200ms }
.toast-enter-from { opacity: 0; transform: translateY(12px) }
.toast-leave-to   { opacity: 0; transform: translateY(-8px) }
</style>
