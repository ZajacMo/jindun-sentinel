<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleCloseFilled, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import { isSeverityCode } from '@/utils/codes'
import { severityLabelKey } from '@/utils/codes'

/**
 * The severity of an alert.
 *
 * The three severities are distinguished by an icon shape *and* a text label,
 * so they stay readable without relying on the hue alone.
 */
const props = defineProps<{ severity: string }>()

const { t } = useI18n()

const icon = computed(() => {
  if (!isSeverityCode(props.severity)) {
    return InfoFilled
  }
  if (props.severity === 'P1') {
    return CircleCloseFilled
  }
  if (props.severity === 'P2') {
    return WarningFilled
  }
  return InfoFilled
})

const label = computed(() =>
  isSeverityCode(props.severity) ? t(severityLabelKey(props.severity)) : props.severity,
)

const modifier = computed(() => (isSeverityCode(props.severity) ? props.severity : 'P3'))
</script>

<template>
  <span class="jd-severity" :class="`jd-severity--${modifier}`">
    <el-icon aria-hidden="true"><component :is="icon" /></el-icon>
    <span>{{ label }}</span>
  </span>
</template>
