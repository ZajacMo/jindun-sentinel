<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataState from '@/components/DataState.vue'
import QualityBadge from '@/components/QualityBadge.vue'
import QualityGateMechanism from '@/components/diagrams/QualityGateMechanism.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'

/**
 * The data quality page.
 *
 * The verdict of the quality gate for every fetched series of the selected
 * economy, with the individual checks that produced it.
 */
const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

const resource = computed(() => data.qualityByCountry[prefs.countryCode] ?? null)
const payload = computed(() => resource.value?.data ?? null)

const series = computed(() => payload.value?.series ?? [])

/** The names of the quality checks, as the pipeline reports them. */
const CHECK_NAMES = [
  'has_observations',
  'enough_observations',
  'unique_dates',
  'ordered_dates',
  'completeness',
  'max_gap',
  'freshness',
]

const gateChecks = computed(() => CHECK_NAMES)

const counts = computed(
  () => payload.value?.counts ?? { total: 0, ok: 0, warning: 0, failure: 0 },
)

onMounted(() => {
  void data.loadQuality(prefs.countryCode)
})

watch(
  () => prefs.countryCode,
  () => {
    void data.loadQuality(prefs.countryCode)
  },
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ t('nav.dataQuality') }}</h1>
        <p>
          {{ t('common.updatedAt', { date: format.dateTime(payload?.generatedAt ?? null) }) }}
        </p>
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
      @retry="data.loadQuality(prefs.countryCode)"
    >
      <div class="jd-stack">
        <section class="jd-kpi-row">
          <div class="jd-kpi">
            <span class="jd-kpi__label">{{ t('quality.ok') }}</span>
            <span class="jd-kpi__value">{{ counts.ok }}</span>
          </div>
          <div class="jd-kpi">
            <span class="jd-kpi__label">{{ t('quality.warning') }}</span>
            <span class="jd-kpi__value">{{ counts.warning }}</span>
          </div>
          <div class="jd-kpi">
            <span class="jd-kpi__label">{{ t('quality.failure') }}</span>
            <span class="jd-kpi__value">{{ counts.failure }}</span>
          </div>
          <div class="jd-kpi">
            <span class="jd-kpi__label">{{ t('unit.count') }}</span>
            <span class="jd-kpi__value">{{ counts.total }}</span>
          </div>
        </section>

        <section class="jd-panel">
          <h2>{{ t('nav.dataQuality') }}</h2>
          <el-table :data="series" border stripe>
            <el-table-column type="expand">
              <template #default="scope">
                <ul v-if="scope?.row" class="jd-check-list">
                  <li v-for="check in scope.row.checks" :key="check.name">
                    <QualityBadge :status="check.severity" />
                    <span class="jd-check-list__name">{{ check.name }}</span>
                    <span class="jd-numeric">
                      {{ check.measured === null ? '—' : check.measured }}
                    </span>
                    <span class="jd-numeric">
                      {{ check.threshold === null ? '—' : check.threshold }}
                    </span>
                  </li>
                </ul>
              </template>
            </el-table-column>
            <el-table-column prop="seriesId" :label="t('common.source')" min-width="260" />
            <el-table-column prop="adapter" :label="t('metric.bucket')" width="160" />
            <el-table-column :label="t('nav.dataQuality')" width="140">
              <template #default="scope">
                <QualityBadge :status="scope.row.severity" />
              </template>
            </el-table-column>
            <el-table-column :label="t('unit.count')" width="120" class-name="jd-numeric">
              <template #default="scope">
                <span class="jd-numeric">{{ scope.row.observations }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('time.day')" width="170">
              <template #default="scope">
                {{ format.date(scope.row.lastDate) }}
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="jd-panel">
          <h2>{{ t('nav.dataQuality') }}</h2>
          <QualityGateMechanism
            :title="t('nav.dataQuality')"
            :source="t('common.source')"
            :checks="gateChecks"
            :verdict="t('nav.dataQuality')"
            :publish="t('quality.ok')"
            :block="t('quality.failure')"
          />
        </section>
      </div>
    </DataState>
  </div>
</template>

<style scoped>
.jd-check-list {
  list-style: none;
  margin: 6px 0;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.jd-check-list__name {
  display: inline-block;
  min-width: 240px;
}
</style>
