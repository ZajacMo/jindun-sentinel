<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import CountrySelector from '@/components/CountrySelector.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'

const { t } = useI18n()
</script>

<template>
  <header class="jd-header">
    <div class="jd-header__brand">
      <span class="jd-header__name">{{ t('app.name') }}</span>
      <span class="jd-header__tagline">{{ t('app.tagline') }}</span>
    </div>
    <div class="jd-header__controls">
      <CountrySelector />
      <LanguageSwitcher />
      <ThemeToggle />
    </div>
  </header>
</template>

<style scoped>
.jd-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jd-gap);
  padding: 12px var(--jd-gap);
  background: var(--jd-surface);
  border-bottom: 1px solid var(--jd-border);
}

.jd-header__brand {
  display: flex;
  flex-direction: column;
}

.jd-header__name {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.jd-header__tagline {
  font-size: 0.82rem;
  color: var(--jd-text-muted);
}

.jd-header__controls {
  display: flex;
  align-items: center;
  gap: var(--jd-gap-sm);
  flex-wrap: wrap;
}
</style>
