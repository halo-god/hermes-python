<script setup lang="ts">
import ModalShell from "@/components/ModalShell.vue";
import type { ConfirmationRequest } from "@/types";

withDefaults(
  defineProps<{
    // AI confirmation mode
    request?: ConfirmationRequest;
    // Classic dialog mode
    title?: string;
    message?: string;
    confirmText?: string;
    danger?: boolean;
  }>(),
  { title: "确认操作", confirmText: "确认", danger: false }
);

const emit = defineEmits<{
  close: [];
  confirm: [];
  respond: [choice: string];
}>();
</script>

<template>
  <!-- AI Confirmation Mode -->
  <template v-if="request">
    <Teleport to="body">
      <div class="confirm-overlay" @click.self="emit('close')">
        <div class="confirm-modal">
          <div class="confirm-header">
            <span class="confirm-icon">🤔</span>
            <div>
              <div class="confirm-title">需要您的确认</div>
              <div class="confirm-sub">AI 在继续前需要您做出选择</div>
            </div>
          </div>
          <div class="confirm-question">{{ request.question }}</div>
          <div class="confirm-options">
            <button
              v-for="opt in request.options"
              :key="opt"
              class="confirm-option"
              @click="emit('respond', opt)"
            >
              {{ opt }}
            </button>
          </div>
          <div class="confirm-footer">
            <button class="btn" @click="emit('respond', 'deny')">跳过</button>
          </div>
        </div>
      </div>
    </Teleport>
  </template>

  <!-- Classic Dialog Mode -->
  <template v-else>
    <ModalShell :title="title" :width="420" @close="emit('close')">
      <p style="font-size: 13.5px; color: var(--ink-soft); line-height: 1.6; margin: 0">{{ message }}</p>
      <template #foot>
        <div style="display: flex; gap: 8px; justify-content: flex-end; width: 100%">
          <button class="btn" @click="emit('close')">取消</button>
          <button
            class="btn"
            :style="danger ? 'color:#fff;background:var(--danger);border-color:var(--danger)' : 'color:#fff;background:var(--accent);border-color:var(--accent)'"
            @click="emit('confirm')"
          >
            {{ confirmText }}
          </button>
        </div>
      </template>
    </ModalShell>
  </template>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(3px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.confirm-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  width: min(520px, 92vw);
  padding: 28px;
}
.confirm-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.confirm-icon {
  font-size: 28px;
  line-height: 1;
}
.confirm-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.confirm-sub {
  font-size: 12px;
  color: var(--ink-mute);
  margin-top: 2px;
}
.confirm-question {
  font-size: 14px;
  color: var(--ink);
  line-height: 1.6;
  margin-bottom: 20px;
  padding: 14px 16px;
  background: var(--bg-panel);
  border-radius: 10px;
  border: 1px solid var(--rule);
}
.confirm-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 18px;
}
.confirm-option {
  width: 100%;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1.5px solid var(--rule);
  background: var(--bg-panel);
  color: var(--ink);
  font-size: 13.5px;
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms, background 160ms;
}
.confirm-option:hover {
  border-color: var(--accent);
  background: var(--accent-tint);
  color: var(--accent-deep);
}
.confirm-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--rule-soft);
  padding-top: 14px;
}
</style>
