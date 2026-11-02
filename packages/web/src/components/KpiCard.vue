<script setup lang="ts">
/** A single headline number of the overview. */
defineProps<{
  label: string
  value: string
  hint?: string
}>()
</script>

<template>
  <div class="jd-kpi">
    <span class="jd-kpi__label">{{ label }}</span>
    <span class="jd-kpi__value">{{ value }}</span>
    <span v-if="hint" class="jd-kpi__hint">{{ hint }}</span>
  </div>
</template>
