<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()

/** The navigation entries, in the order they are shown. */
const items = [
  { name: 'overview', key: 'nav.overview' },
  { name: 'countries', key: 'nav.countries' },
  { name: 'spillover', key: 'nav.spillover' },
  { name: 'alerts', key: 'nav.alerts' },
  { name: 'data-quality', key: 'nav.dataQuality' },
  { name: 'methodology', key: 'nav.methodology' },
] as const

function isActive(name: string): boolean {
  const current = route.name
  if (name === 'countries') {
    return current === 'countries' || current === 'country-detail'
  }
  return current === name
}
</script>

<template>
  <nav class="jd-nav" :aria-label="t('app.name')">
    <router-link
      v-for="item in items"
      :key="item.name"
      class="jd-nav__link"
      :class="{ 'jd-nav__link--active': isActive(item.name) }"
      :to="{ name: item.name }"
    >
      {{ t(item.key) }}
    </router-link>
  </nav>
</template>

<style scoped>
.jd-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 var(--jd-gap);
  background: var(--jd-surface);
  border-bottom: 1px solid var(--jd-border);
}

.jd-nav__link {
  padding: 10px 14px;
  color: var(--jd-text-muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  font-weight: 500;
}

.jd-nav__link:hover {
  color: var(--jd-text);
}

.jd-nav__link--active {
  color: var(--jd-accent);
  border-bottom-color: var(--jd-accent);
}
</style>
