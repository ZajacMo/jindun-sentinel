<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleCheckFilled, CircleCloseFilled, WarningFilled } from '@element-plus/icons-vue'
import { qualityLabelKey } from '@/utils/codes'

/** The verdict of a data-quality gate. */
const props = defineProps<{ status: string }>()

const { t } = useI18n()

const icon = computed(() => {
  if (props.status === 'failure') {
    return CircleCloseFilled
  }
  if (props.status === 'warning') {
    return WarningFilled
  }
  return CircleCheckFilled
})

const modifier = computed(() =>
  props.status === 'failure' || props.status === 'warning' ? props.status : 'ok',
)

const label = computed(() => t(qualityLabelKey(props.status)))
</script>

<template>
  <span class="jd-quality" :class="`jd-quality--${modifier}`">
    <el-icon aria-hidden="true"><component :is="icon" /></el-icon>
    <span>{{ label }}</span>
  </span>
</template>
