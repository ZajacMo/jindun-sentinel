<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { LOCALE_LABELS, SUPPORTED_LOCALES } from '@/i18n/catalogue'
import type { SupportedLocale } from '@/i18n/catalogue'
import { usePrefsStore } from '@/stores/prefs'

const { t } = useI18n()
const prefs = usePrefsStore()

const current = computed({
  get: () => prefs.locale,
  set: (value: SupportedLocale) => prefs.setLocale(value),
})

/** The language names are written in the language itself; they are not messages. */
const options = SUPPORTED_LOCALES.map((code) => ({
  value: code,
  label: LOCALE_LABELS[code],
}))
</script>

<template>
  <label class="jd-lang">
    <span class="jd-lang__label">{{ t('nav.language') }}</span>
    <el-select v-model="current" size="default" class="jd-lang__select">
      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </el-select>
  </label>
</template>

<style scoped>
.jd-lang {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.jd-lang__label {
  font-size: 0.82rem;
  color: var(--jd-text-muted);
}

.jd-lang__select {
  width: 130px;
}
</style>
