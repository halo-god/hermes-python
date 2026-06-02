<script setup lang="ts">
/* 1:1 port of the prototype composer (hermes-app.js Composer): rich toolbar +
   profile dropdown (ACP) + circular send button. */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Icon from "@/components/Icon.vue";
import { agentsApi, type Profile } from "@/api/agents";
import { useNotificationStore } from "@/stores/notifications";

const ns = useNotificationStore();

const props = defineProps<{
  modelValue: string;
  placeholder?: string;
  agent?: { label?: string; color?: string | null; model?: string } | null;
  streaming?: boolean;
  autofocus?: boolean;
  conversationId?: string;
}>();
export interface SendOptions {
  profileId?: string;
  webSearch?: boolean;
  deepThink?: boolean;
  stagedFiles?: File[];
}

const emit = defineEmits<{ "update:modelValue": [string]; send: [SendOptions] }>();

const ta = ref<HTMLTextAreaElement | null>(null);
const wrap = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const showProfile = ref(false);
const showAttach = ref(false);
const webSearch = ref(false);
const deepThink = ref(false);
const profiles = ref<Profile[]>([]);
const selected = ref<Profile | null>(null);
const stagedFiles = ref<File[]>([]);

onMounted(async () => {
  document.addEventListener("mousedown", onDocClick);
  try {
    profiles.value = await agentsApi.profiles();
    selected.value = profiles.value[0] || null;
  } catch {
    /* ignore */
  }
});
onBeforeUnmount(() => document.removeEventListener("mousedown", onDocClick));
function onDocClick(e: MouseEvent) {
  if (wrap.value && !wrap.value.contains(e.target as Node)) {
    showProfile.value = false;
    showAttach.value = false;
  }
}

const personal = computed(() => profiles.value.filter((p) => p.scope === "personal"));
const team = computed(() => profiles.value.filter((p) => p.scope === "team"));
const pillLabel = computed(() => selected.value?.name || props.agent?.label || "Hermes");
const pillColor = computed(() => selected.value?.color || props.agent?.color || "#b8852a");
const pillModel = computed(() => selected.value?.default_model || props.agent?.model || "ACP");

function autoresize() {
  const el = ta.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(220, Math.max(el.scrollHeight, 84)) + "px";
}
function onInput(e: Event) {
  emit("update:modelValue", (e.target as HTMLTextAreaElement).value);
  autoresize();
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    if (props.modelValue.trim() && !props.streaming) doSend();
  }
}
function doSend() {
  const files = stagedFiles.value.length ? [...stagedFiles.value] : undefined;
  stagedFiles.value = [];
  emit("send", { profileId: selected.value?.id, webSearch: webSearch.value, deepThink: deepThink.value, stagedFiles: files });
}
function pickProfile(p: Profile) {
  selected.value = p;
  showProfile.value = false;
}
function removeStagedFile(idx: number) {
  stagedFiles.value.splice(idx, 1);
}

function triggerUpload() {
  showAttach.value = false;
  fileInput.value?.click();
}

function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  stagedFiles.value.push(file);
  ns.toast(`已添加 ${file.name}`);
  if (fileInput.value) fileInput.value.value = "";
}
</script>

<template>
  <div class="composer-wrap" ref="wrap">
    <input ref="fileInput" type="file" style="display:none" @change="onFileSelected" />
    <!-- staged file chips -->
    <div v-if="stagedFiles.length" class="staged-files">
      <span v-for="(f, i) in stagedFiles" :key="i" class="staged-chip">
        <Icon name="paperclip" :size="11" />
        <span class="staged-name">{{ f.name }}</span>
        <button class="staged-rm" @click="removeStagedFile(i)">×</button>
      </span>
    </div>
    <div class="composer">
      <textarea
        ref="ta"
        class="composer-input"
        :placeholder="placeholder"
        :value="modelValue"
        :autofocus="autofocus"
        rows="1"
        @input="onInput"
        @keydown="onKey"
      ></textarea>
      <div class="composer-toolbar">
        <div style="position: relative">
          <button class="composer-tool" :class="{ active: showAttach }" title="附件" @click="showAttach = !showAttach"><Icon name="paperclip" /></button>
          <div v-if="showAttach" class="menu" style="bottom: 120%; left: 0; min-width: 220px">
            <div class="menu-label">添加到会话</div>
            <button class="menu-item" @click="triggerUpload">
              <Icon name="paperclip" /><span class="m-name">上传本地文件</span>
            </button>
            <button class="menu-item" @click="showAttach = false"><Icon name="doc" /><span class="m-name">引用知识库</span></button>
            <button class="menu-item" @click="showAttach = false"><Icon name="globe" /><span class="m-name">粘贴网页链接</span></button>
          </div>
        </div>
        <button class="composer-tool" :class="{ active: webSearch }" title="网页搜索" @click="webSearch = !webSearch"><Icon name="globe" /> 联网</button>
        <button class="composer-tool" :class="{ active: deepThink }" title="思考模式" @click="deepThink = !deepThink"><Icon name="sparkle" /> 深思</button>
        <span class="composer-spacer"></span>
        <div style="position: relative">
          <button class="model-pick" title="切换 Hermes Profile · ACP 会话" @click="showProfile = !showProfile">
            <span class="profile-dot" :style="{ background: pillColor }"></span>
            {{ pillLabel }}
            <span class="profile-model">{{ pillModel }}</span>
            <Icon name="chevron_down" />
          </button>
          <div v-if="showProfile" class="menu" style="bottom: 110%; right: 0; min-width: 320px">
            <div class="menu-label">个人 Profile</div>
            <button v-for="p in personal" :key="p.id" class="menu-item profile-item" :class="{ active: selected?.id === p.id }" @click="pickProfile(p)">
              <span class="profile-avatar" :style="{ background: p.color }"><Icon :name="p.icon" /></span>
              <div class="profile-meta"><div class="profile-name">{{ p.name }} <span class="profile-handle">@{{ p.handle }}</span></div><div class="profile-desc">{{ p.desc }}</div></div>
              <span class="profile-tag">{{ p.default_model }}</span>
            </button>
            <div class="menu-sep"></div>
            <div class="menu-label">团队 Profile · 共享记忆</div>
            <button v-for="p in team" :key="p.id" class="menu-item profile-item" :class="{ active: selected?.id === p.id }" @click="pickProfile(p)">
              <span class="profile-avatar" :style="{ background: p.color }"><Icon :name="p.icon" /></span>
              <div class="profile-meta"><div class="profile-name">{{ p.name }} <span class="profile-handle">@{{ p.handle }}</span></div><div class="profile-desc">{{ p.desc }}</div></div>
              <span class="profile-tag">{{ p.default_model }}</span>
            </button>
            <div class="menu-foot-acp"><Icon name="bolt" /> 通过 ACP · v1 协议建立会话</div>
          </div>
        </div>
        <button
          class="send-btn"
          :class="{ armed: modelValue.trim() && !streaming, disabled: !modelValue.trim() || streaming }"
          title="发送"
          @click="modelValue.trim() && !streaming && doSend()"
        >
          <Icon name="arrow_up" />
        </button>
      </div>
    </div>
  </div>
</template>
