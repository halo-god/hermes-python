<script setup lang="ts">
import { ref, onMounted } from "vue";
import ModalShell from "@/components/ModalShell.vue";
import { teamsApi } from "@/api/teams";

const props = defineProps<{
  teamId: string;
  editing?: { id: string; name: string; kind: string; size_bytes: number } | null;
}>();

const emit = defineEmits<{ close: []; saved: [] }>();

const form = ref({ name: "", kind: "pdf", size_bytes: 0 });
const saving = ref(false);
const KINDS = ["pdf", "doc", "txt", "csv", "md", "json", "html", "xlsx"];

onMounted(() => {
  if (props.editing) {
    form.value = {
      name: props.editing.name,
      kind: props.editing.kind,
      size_bytes: props.editing.size_bytes,
    };
  }
});

async function save() {
  if (!form.value.name.trim()) return;
  saving.value = true;
  try {
    if (props.editing) {
      await teamsApi.updateKnowledge(props.teamId, props.editing.id, {
        name: form.value.name.trim(),
        kind: form.value.kind,
        size_bytes: form.value.size_bytes,
      });
    } else {
      await teamsApi.addKnowledge(props.teamId, {
        name: form.value.name.trim(),
        kind: form.value.kind,
        size_bytes: form.value.size_bytes || Math.round(Math.random() * 900 + 60) * 1024,
      });
    }
    emit("saved");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <ModalShell :title="editing ? '编辑知识条目' : '上传知识文件'" :width="480" @close="emit('close')">
    <div style="display: flex; flex-direction: column; gap: 14px">
      <div>
        <label style="font-size: 12.5px; font-weight: 500; color: var(--ink-mute); display: block; margin-bottom: 4px">文件名称</label>
        <input
          v-model="form.name"
          type="text"
          placeholder="如 品牌指南.pdf"
          style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--surface); color: var(--ink); outline: none"
          @keydown.enter="save"
        />
      </div>
      <div style="display: flex; gap: 12px">
        <div style="flex: 1">
          <label style="font-size: 12.5px; font-weight: 500; color: var(--ink-mute); display: block; margin-bottom: 4px">文件类型</label>
          <select
            v-model="form.kind"
            style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--surface); color: var(--ink); outline: none"
          >
            <option v-for="k in KINDS" :key="k" :value="k">{{ k.toUpperCase() }}</option>
          </select>
        </div>
        <div style="flex: 1">
          <label style="font-size: 12.5px; font-weight: 500; color: var(--ink-mute); display: block; margin-bottom: 4px">文件大小 (字节)</label>
          <input
            v-model.number="form.size_bytes"
            type="number"
            placeholder="留空自动生成"
            style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--surface); color: var(--ink); outline: none"
          />
        </div>
      </div>
    </div>
    <template #foot>
      <div style="display: flex; gap: 8px; justify-content: flex-end; width: 100%">
        <button class="btn" @click="emit('close')">取消</button>
        <button class="btn primary" :disabled="!form.name.trim() || saving" @click="save">
          {{ saving ? "保存中..." : (editing ? "更新" : "上传") }}
        </button>
      </div>
    </template>
  </ModalShell>
</template>
