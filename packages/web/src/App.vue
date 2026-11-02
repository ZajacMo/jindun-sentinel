<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppHeader from '@/components/AppHeader.vue'
import AppNav from '@/components/AppNav.vue'

const { t } = useI18n()
</script>

<template>
  <div class="jd-shell">
    <a class="jd-skip-link" href="#jd-main">{{ t('app.name') }}</a>
    <AppHeader />
    <AppNav />
    <main id="jd-main" class="jd-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.jd-skip-link {
  position: absolute;
  left: -10000px;
  top: 0;
  background: var(--jd-surface);
  color: var(--jd-text);
  padding: 8px 12px;
  border-radius: var(--jd-radius-sm);
  z-index: 10;
}

.jd-skip-link:focus {
  left: 8px;
  top: 8px;
}
</style>
