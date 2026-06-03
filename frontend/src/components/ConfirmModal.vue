<script setup lang="ts">
import { ref, watch } from "vue";
import type { ConfirmationRequest } from "@/types";

const props = withDefaults(
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

// Multi-select state
const selected = ref<Set<string>>(new Set());

// Reset selection when request changes
watch(
  () => props.request,
  () => {
    selected.value = new Set();
  },
  { immediate: true }
);

function toggle(opt: string) {
  if (selected.value.has(opt)) {
    selected.value.delete(opt);
  } else {
    selected.value.add(opt);
  }
  // Force reactivity
  selected.value = new Set(selected.value);
}

function submitSelection() {
  if (selected.value.size === 0) return;
  const choice = Array.from(selected.value).join(", ");
  emit("respond", choice);
}

function isMultiSelect(): boolean {
  return (props.request?.options?.length || 0) > 2;
}
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
              <div class="confirm-sub">
                {{ isMultiSelect() ? "可多选，选完点击确认" : "请选择一个选项" }}
              </div>
            </div>
          </div>
          <div class="confirm-question">{{ request.question }}</div>
          <div class="confirm-options">
            <button
              v-for="opt in request.options"
              :key="opt"
              class="confirm-option"
              :class="{ selected: selected.has(opt) }"
              @click="isMultiSelect() ? toggle(opt) : emit('respond', opt)"
            >
              <span v-if="isMultiSelect()" class="checkbox" :class="{ checked: selected.has(opt) }">
                {{ selected.has(opt) ? "✓" : "" }}
              </span>
              {{ opt }}
            </button>
          </div>
          <div class="confirm-footer">
            <button class="btn" @click="emit('respond', 'deny')">跳过</button>
            <button
              v-if="isMultiSelect()"
              class="btn btn-primary"
              :disabled="selected.size === 0"
              @click="submitSelection"
            >
              确认选择 ({{ selected.size }})
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </template>

  <!-- Classic Dialog Mode -->
  <template v-else>
    <Teleport to="body">
      <div class="confirm-overlay" @click.self="emit('close')">
        <div class="confirm-modal" style="max-width: 420px">
          <div class="confirm-question">{{ message }}</div>
          <div class="confirm-footer">
            <button class="btn" @click="emit('close')">取消</button>
            <button
              class="btn"
              :style="danger ? 'color:#fff;background:var(--danger);border-color:var(--danger)' : 'color:#fff;background:var(--accent);border-color:var(--accent)'"
              @click="emit('confirm')"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
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
  display: flex;
  align-items: center;
  gap: 10px;
}
.confirm-option:hover {
  border-color: var(--accent);
  background: var(--accent-tint);
  color: var(--accent-deep);
}
.confirm-option.selected {
  border-color: var(--accent);
  background: var(--accent-tint);
  color: var(--accent-deep);
}
.checkbox {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1.5px solid var(--rule);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  transition: all 160ms;
}
.checkbox.checked {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}
.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--rule-soft);
  padding-top: 14px;
}
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid var(--rule);
  background: var(--surface);
  color: var(--ink);
  font-size: 13px;
  cursor: pointer;
  transition: all 160ms;
}
.btn:hover {
  border-color: var(--accent);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
