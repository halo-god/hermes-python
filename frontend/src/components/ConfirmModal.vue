<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { ConfirmationRequest } from "@/types";

const props = withDefaults(
  defineProps<{
    request?: ConfirmationRequest;
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

// Multi-step wizard state
const currentStep = ref(0);
const answers = ref<string[]>([]);

// Determine if multi-question mode
const isMultiQuestion = computed(() => {
  return (props.request?.questions?.length || 0) > 0;
});

// Current question's options
const currentOptions = computed(() => {
  if (isMultiQuestion.value && props.request?.questions) {
    return props.request.questions[currentStep.value]?.options || [];
  }
  return props.request?.options || [];
});

// Current question text
const currentQuestion = computed(() => {
  if (isMultiQuestion.value && props.request?.questions) {
    return props.request.questions[currentStep.value]?.question || "";
  }
  return props.request?.question || "";
});

// Total steps
const totalSteps = computed(() => {
  if (isMultiQuestion.value && props.request?.questions) {
    return props.request.questions.length;
  }
  return 1;
});

// Is this the last step?
const isLastStep = computed(() => currentStep.value >= totalSteps.value - 1);

// Reset when request changes
watch(
  () => props.request,
  () => {
    currentStep.value = 0;
    answers.value = [];
  },
  { immediate: true }
);

function selectOption(opt: string) {
  if (isMultiQuestion.value) {
    // Record answer and advance
    answers.value[currentStep.value] = opt;
    if (isLastStep.value) {
      submitAll();
    } else {
      currentStep.value++;
    }
  } else {
    // Single question: emit immediately
    emit("respond", opt);
  }
}

function submitAll() {
  if (!props.request?.questions) return;
  // Build summary: "Q1: A, Q2: B, Q3: C"
  const parts = props.request.questions.map((q, i) => {
    const answer = answers.value[i] || "跳过";
    return `${q.question}: ${answer}`;
  });
  emit("respond", parts.join("; "));
}

function goBack() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}
</script>

<template>
  <template v-if="request">
    <Teleport to="body">
      <div class="confirm-overlay" @click.self="emit('close')">
        <div class="confirm-modal">
          <div class="confirm-header">
            <span class="confirm-icon">🤔</span>
            <div>
              <div class="confirm-title">
                {{ isMultiQuestion ? `问题 ${currentStep + 1} / ${totalSteps}` : "需要您的确认" }}
              </div>
              <div class="confirm-sub">
                {{ request.question || "AI 在继续前需要您做出选择" }}
              </div>
            </div>
          </div>

          <!-- Progress bar for multi-step -->
          <div v-if="isMultiQuestion" class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: `${((currentStep + 1) / totalSteps) * 100}%` }"
            />
          </div>

          <!-- Current question -->
          <div class="confirm-question">{{ currentQuestion }}</div>

          <!-- Options -->
          <div class="confirm-options">
            <button
              v-for="opt in currentOptions"
              :key="opt"
              class="confirm-option"
              @click="selectOption(opt)"
            >
              {{ opt }}
            </button>
          </div>

          <!-- Footer -->
          <div class="confirm-footer">
            <button class="btn" @click="emit('respond', 'deny')">跳过全部</button>
            <button
              v-if="isMultiQuestion && currentStep > 0"
              class="btn"
              @click="goBack"
            >
              上一步
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
.progress-bar {
  height: 4px;
  background: var(--rule);
  border-radius: 2px;
  margin-bottom: 18px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 300ms ease;
}
.confirm-question {
  font-size: 14px;
  font-weight: 500;
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
</style>
