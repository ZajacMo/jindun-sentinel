<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useLabels } from '@/composables/useLabels'

const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const labels = useLabels()

const options = computed(() => {
  const countries = data.countries.data ?? []
  return countries.map((country) => ({
    value: country.code,
    label: labels.country(country.code),
  }))
})

const current = computed({
  get: () => prefs.countryCode,
  set: (value: string) => prefs.setCountry(value),
})

onMounted(() => {
  void data.loadCountries()
})
</script>

<template>
  <label class="jd-country">
    <span class="jd-country__label">{{ t('scope.country') }}</span>
    <el-select v-model="current" size="default" class="jd-country__select">
      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
      <el-option v-if="options.length === 0" :label="prefs.countryCode" :value="prefs.countryCode" />
    </el-select>
  </label>
</template>

<style scoped>
.jd-country {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.jd-country__label {
  font-size: 0.82rem;
  color: var(--jd-text-muted);
}

.jd-country__select {
  width: 150px;
}
</style>
