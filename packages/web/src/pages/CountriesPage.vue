<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataState from '@/components/DataState.vue'
import MarketIndexMechanism from '@/components/diagrams/MarketIndexMechanism.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import { indicatorLabelKey } from '@/utils/codes'

/**
 * The country explorer.
 *
 * A selector for the monitored economy and the table of its market indices,
 * with the weights of the tertiary indicators each market index is built from.
 */
const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

/** Method names are not translated. */
const METHOD_PCA = 'PCA'
const METHOD_CRITIC = 'CRITIC'
const resource = computed(() => data.indexByCountry[prefs.countryCode] ?? null)
const payload = computed(() => resource.value?.data ?? null)

const markets = computed(() => payload.value?.marketIndices ?? [])

const rows = computed(() =>
  markets.value.map((market) => ({
    code: market.code,
    label: labels.market(market.code),
    weight: market.weight ?? null,
    latest: market.points.at(-1)?.value ?? null,
    asOf: market.points.at(-1)?.date ?? null,
    indicators: market.indicators.map((indicator) => ({
      code: indicator.code,
      label: t(indicatorLabelKey(indicator.code, indicator.labelKey)),
      weight: indicator.weight,
      unit: indicator.unit ?? null,
    })),
  })),
)

const indexStages = computed(() => [
  { label: t('common.source') },
  { label: t('index.percentile') },
  { label: METHOD_PCA },
  { label: METHOD_CRITIC },
  { label: t('metric.sector') },
  { label: t('index.composite') },
])

watch(
  () => prefs.countryCode,
  () => {
    void data.loadIndex(prefs.countryCode, prefs.lens)
  },
  { immediate: true },
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ t('nav.countries') }}</h1>
        <p>{{ labels.country(prefs.countryCode) }}</p>
      </div>
      <el-select
        :model-value="prefs.countryCode"
        size="default"
        style="width: 180px"
        @update:model-value="prefs.setCountry($event as string)"
      >
        <el-option
          v-for="country in data.countries.data ?? []"
          :key="country.code"
          :label="labels.country(country.code)"
          :value="country.code"
        />
      </el-select>
    </header>

    <DataState
      :status="resource?.status ?? 'idle'"
      :error="resource?.error ?? null"
      :empty="!payload"
      @retry="data.loadIndex(prefs.countryCode, prefs.lens)"
    >
      <div class="jd-stack">
        <section class="jd-panel">
          <h2>{{ t('metric.sector') }} — {{ t('index.composite') }}</h2>
          <el-table :data="rows" border stripe>
            <el-table-column type="expand">
              <template #default="scope">
                <ul v-if="scope?.row" class="jd-indicator-list">
                  <li v-for="indicator in scope.row.indicators" :key="indicator.code">
                    <span class="jd-indicator-list__name">{{ indicator.label }}</span>
                    <span class="jd-numeric">{{ format.percent(indicator.weight, 2) }}</span>
                    <span class="jd-muted">
                      {{ indicator.unit ? labels.unit(indicator.unit) : '' }}
                    </span>
                  </li>
                </ul>
              </template>
            </el-table-column>
            <el-table-column :label="t('metric.sector')" min-width="160">
              <template #default="scope">
                <router-link :to="{ name: 'country-detail', params: { code: prefs.countryCode } }">
                  {{ scope.row.label }}
                </router-link>
              </template>
            </el-table-column>
            <el-table-column :label="t('index.composite')" width="160" class-name="jd-numeric">
              <template #default="scope">
                <span class="jd-numeric">{{ format.number(scope.row.latest, 4) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('metric.ownShare')" width="140" class-name="jd-numeric">
              <template #default="scope">
                <span class="jd-numeric">{{ format.percent(scope.row.weight, 2) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('time.day')" width="170">
              <template #default="scope">
                {{ format.date(scope.row.asOf) }}
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="jd-panel">
          <h2>{{ t('index.percentile') }}</h2>
          <MarketIndexMechanism
            :title="t('index.composite')"
            :stages="indexStages"
            :composite="t('index.composite')"
          />
        </section>
      </div>
    </DataState>
  </div>
</template>

<style scoped>
.jd-indicator-list {
  list-style: none;
  margin: 6px 0;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.jd-indicator-list__name {
  display: inline-block;
  min-width: 260px;
}
</style>
