<script setup lang="ts">
import Icon from "@/components/Icon.vue";
withDefaults(defineProps<{ title: string; subtitle?: string; width?: number }>(), { width: 560 });
defineEmits<{ close: [] }>();
</script>

<template>
  <div class="modal-scrim" @mousedown.self="$emit('close')">
    <div class="modal" :style="{ maxWidth: width + 'px' }" role="dialog">
      <div class="modal-head">
        <div>
          <div class="modal-title">{{ title }}</div>
          <div v-if="subtitle" class="modal-sub">{{ subtitle }}</div>
        </div>
        <button class="modal-close" @click="$emit('close')" aria-label="关闭"><Icon name="close" /></button>
      </div>
      <div class="modal-body"><slot /></div>
      <div class="modal-foot"><slot name="foot" /></div>
    </div>
  </div>
</template>
