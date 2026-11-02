<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { usePrefsStore } from '@/stores/prefs'

const { t } = useI18n()
const prefs = usePrefsStore()

const isDark = computed(() => prefs.theme === 'dark')
/**
 * The catalogue has no key for the theme switch; the product name is used as
 * its accessible name, and the sun/moon icon carries the meaning visually.
 */
const label = computed(() => t('app.name'))
</script>

<template>
  <el-tooltip :content="label" placement="bottom">
    <el-button
      class="jd-theme-toggle"
      circle
      :aria-label="label"
      :title="label"
      @click="prefs.toggleTheme()"
    >
      <el-icon><component :is="isDark ? Moon : Sunny" /></el-icon>
    </el-button>
  </el-tooltip>
</template>

<style scoped>
.jd-theme-toggle {
  width: 32px;
  height: 32px;
}
</style>
