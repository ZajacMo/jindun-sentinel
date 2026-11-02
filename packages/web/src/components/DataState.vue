<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Refresh } from '@element-plus/icons-vue'
import type { ResourceStatus } from '@/stores/data'

/**
 * Renders the state of a resource: loading, failed, empty or loaded.
 *
 * A failed request is always shown — the UI never falls back to a silent
 * empty screen.
 */
withDefaults(
  defineProps<{
    status: ResourceStatus
    error?: string | null
    empty?: boolean
  }>(),
  { error: null, empty: false },
)

const emit = defineEmits<{ retry: [] }>()

const { t } = useI18n()
</script>

<template>
  <div class="jd-state">
    <el-alert
      v-if="status === 'error'"
      class="jd-state__alert"
      type="error"
      show-icon
      :closable="false"
      :title="t('common.error')"
      :description="error ?? undefined"
    >
      <template #default>
        <el-button size="small" :icon="Refresh" @click="emit('retry')">
          {{ t('common.retry') }}
        </el-button>
      </template>
    </el-alert>

    <div v-else-if="status === 'loading'" class="jd-state__loading">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="status === 'success' && empty" class="jd-state__empty jd-muted">
      {{ t('common.empty') }}
    </div>

    <slot v-else />
  </div>
</template>

<style scoped>
.jd-state__loading {
  padding: 8px 0;
}

.jd-state__empty {
  padding: 24px 0;
  text-align: center;
}

.jd-state__alert :deep(.el-alert__content) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
</style>
