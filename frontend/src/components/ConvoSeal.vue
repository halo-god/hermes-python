<script setup lang="ts">
/* Procedurally generated SVG seal per conversation.
   Deterministic hash of conversation.id → ring style, petal count, center glyph. */
import { computed } from "vue";

const props = defineProps<{ seed: string; size?: number }>();

const GLYPHS = ["卄", "匕", "卩", "凵", "彡", "爻", "勹", "匚", "囗", "廿"];

const seal = computed(() => {
  const id = props.seed || "x";
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (((h << 5) - h + id.charCodeAt(i)) | 0) >>> 0;
  const rand = (n: number) => {
    h = ((h * 1103515245 + 12345) & 0x7fffffff) >>> 0;
    return h % n;
  };

  const ring = rand(3); // 0=dashed,1=double,2=solid
  const segs = 6 + rand(5);
  const slices: number[] = [];
  for (let i = 0; i < segs; i++) slices.push(rand(100) < 50 ? 1 : 0);
  const glyph = GLYPHS[rand(GLYPHS.length)];

  // build petal arc paths
  const cx = 20, cy = 20, r = 13;
  const paths: string[] = [];
  const step = (2 * Math.PI) / segs;
  for (let i = 0; i < segs; i++) {
    if (!slices[i]) continue;
    const a1 = step * i - Math.PI / 2;
    const a2 = step * (i + 1) - Math.PI / 2;
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2);
    const y2 = cy + r * Math.sin(a2);
    paths.push(`M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`);
  }

  return { ring, paths, glyph };
});

const sz = computed(() => props.size || 36);
</script>

<template>
  <svg
    :width="sz" :height="sz"
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style="flex-shrink: 0"
  >
    <!-- petal slices -->
    <path v-for="(p, i) in seal.paths" :key="i" :d="p" fill="var(--accent-tint)" stroke="var(--accent)" stroke-width="0.3" />

    <!-- ring variants -->
    <circle v-if="seal.ring === 0" cx="20" cy="20" r="14" stroke="var(--accent)" stroke-width="1" fill="none" stroke-dasharray="2.5 2" />
    <template v-else-if="seal.ring === 1">
      <circle cx="20" cy="20" r="14" stroke="var(--accent)" stroke-width="0.6" fill="none" />
      <circle cx="20" cy="20" r="12" stroke="var(--accent)" stroke-width="0.4" fill="none" />
    </template>
    <circle v-else cx="20" cy="20" r="14" stroke="var(--accent)" stroke-width="1.2" fill="none" />

    <!-- center glyph -->
    <text x="20" y="24" text-anchor="middle" font-family="var(--font-serif)" font-size="10" fill="var(--accent-deep)" font-weight="500">{{ seal.glyph }}</text>
  </svg>
</template>
