<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
onMounted(() => auth.bootstrap());
</script>

<template>
  <router-view v-if="auth.ready" />
  <div v-else class="boot-screen">
    <div class="boot-mark">H</div>
    <div class="boot-text">信使正在准备…</div>
  </div>
</template>

<style scoped>
.boot-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  background: var(--bg-canvas);
}
.boot-mark {
  width: 52px;
  height: 52px;
  border-radius: 13px;
  background: linear-gradient(180deg, #2a241a, #15110b);
  color: var(--accent);
  display: grid;
  place-items: center;
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 600;
}
.boot-text {
  font-family: var(--font-serif);
  font-style: italic;
  color: var(--ink-mute);
}
</style>
