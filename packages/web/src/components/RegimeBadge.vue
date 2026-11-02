<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'
import { isRegimeCode, regimeLabelKey } from '@/utils/codes'

/** The current stress regime, shown as a badge with an icon and a label. */
const props = defineProps<{
  regime: string
  probability?: number | null
}>()

const { t } = useI18n()

const icon = computed(() => (props.regime === 'high' ? WarningFilled : CircleCheckFilled))
const label = computed(() =>
  isRegimeCode(props.regime) ? t(regimeLabelKey(props.regime)) : props.regime,
)
const modifier = computed(() => (props.regime === 'high' ? 'high' : 'moderate'))
</script>

<template>
  <span class="jd-regime" :class="`jd-regime--${modifier}`">
    <el-icon aria-hidden="true"><component :is="icon" /></el-icon>
    <span>{{ label }}</span>
    <span v-if="probability !== undefined && probability !== null" class="jd-numeric">
      {{ probability.toFixed(2) }}
    </span>
  </span>
</template>
