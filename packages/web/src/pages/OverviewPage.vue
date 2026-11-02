<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataState from '@/components/DataState.vue'
import KpiCard from '@/components/KpiCard.vue'
import RegimeBadge from '@/components/RegimeBadge.vue'
import CompositeChart from '@/components/charts/CompositeChart.vue'
import PipelineDiagram from '@/components/diagrams/PipelineDiagram.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import type { SeriesPoint } from '@/api/types'

/**
 * The overview.
 *
 * A single dashboard for the selected economy: the composite stress index,
 * the regime it currently sits in, the two reporting lenses and the KPIs that
 * go with them — plus the mechanism diagram of the daily pipeline that
 * produced all of it.
 */
const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

/**
 * Acronyms and the names of pipeline stages have no catalogue entry and are
 * not translated; they are the technical vocabulary of the methodology.
 */
const STAGE_ADAPTERS = 'Adapters'
const STAGE_PCA = 'PCA'
const STAGE_API = 'API'
const STAGE_UI = 'UI'

const resource = computed(() => data.indexByCountry[prefs.countryCode] ?? null)
const payload = computed(() => resource.value?.data ?? null)

const lensPoints = computed<SeriesPoint[]>(() => {
  const current = payload.value
  if (!current) {
    return []
  }
  return prefs.lens === 'percentile' ? current.percentile : current.deviation
})

const latestComposite = computed(() => payload.value?.composite.at(-1) ?? null)
const latestPercentile = computed(() => payload.value?.percentile.at(-1) ?? null)
const latestDeviation = computed(() => payload.value?.deviation.at(-1) ?? null)
const latestRegime = computed(() => payload.value?.regime.points.at(-1) ?? null)

const pipelineStages = computed(() => [
  { label: t('common.source') },
  { label: STAGE_ADAPTERS },
  { label: t('nav.dataQuality') },
  { label: t('index.percentile') },
  { label: STAGE_PCA },
  { label: t('index.composite') },
  { label: t('regime.probability') },
  { label: t('nav.alerts') },
  { label: STAGE_API },
  { label: STAGE_UI },
])

watch(
  () => [prefs.countryCode, prefs.lens] as const,
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
        <h1>{{ t('nav.overview') }}</h1>
        <p>{{ labels.country(prefs.countryCode) }} — {{ t('app.tagline') }}</p>
      </div>
      <el-radio-group
        :model-value="prefs.lens"
        size="default"
        @update:model-value="prefs.setLens($event as 'percentile' | 'deviation')"
      >
        <el-radio-button value="percentile">{{ t('lens.percentile') }}</el-radio-button>
        <el-radio-button value="deviation">{{ t('lens.deviation') }}</el-radio-button>
      </el-radio-group>
    </header>

    <DataState
      :status="resource?.status ?? 'idle'"
      :error="resource?.error ?? null"
      :empty="!payload"
      @retry="data.loadIndex(prefs.countryCode, prefs.lens)"
    >
      <div class="jd-stack">
        <section class="jd-kpi-row">
          <KpiCard
            :label="t('index.composite')"
            :value="format.number(latestComposite?.value ?? null, 4)"
            :hint="latestComposite ? format.date(latestComposite.date) : ''"
          />
          <KpiCard
            :label="t('index.percentile')"
            :value="format.percent(latestPercentile?.value ?? null, 2)"
            :hint="t('lens.percentile')"
          />
          <KpiCard
            :label="t('index.deviation')"
            :value="format.number(latestDeviation?.value ?? null, 4)"
            :hint="t('lens.deviation')"
          />
          <div class="jd-kpi">
            <span class="jd-kpi__label">{{ t('regime.probability') }}</span>
            <RegimeBadge
              :regime="latestRegime?.regime ?? ''"
              :probability="latestRegime?.probabilityHigh ?? null"
            />
          </div>
          <KpiCard
            :label="t('time.day')"
            :value="format.date(payload?.asOf ?? null)"
            :hint="t('common.updatedAt', { date: format.date(payload?.asOf ?? null) })"
          />
        </section>

        <section class="jd-panel">
          <h2>{{ labels.lens(prefs.lens) }}</h2>
          <CompositeChart :points="lensPoints" :lens="prefs.lens" />
        </section>

        <section class="jd-panel">
          <h2>{{ t('index.composite') }}</h2>
          <PipelineDiagram
            :title="t('index.composite')"
            :stages="pipelineStages"
            :rejection="t('quality.failure')"
          />
        </section>
      </div>
    </DataState>
  </div>
</template>
