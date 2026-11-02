<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import DataState from '@/components/DataState.vue'
import RegimeBadge from '@/components/RegimeBadge.vue'
import CompositeChart from '@/components/charts/CompositeChart.vue'
import MarketIndexChart from '@/components/charts/MarketIndexChart.vue'
import RegimeBandChart from '@/components/charts/RegimeBandChart.vue'
import RegimeMechanism from '@/components/diagrams/RegimeMechanism.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'

/**
 * The country detail.
 *
 * The composite index, the regime probability band, the market indices and
 * the spillover network of one economy — together with the mechanism diagram
 * that explains how the regime and its probability are produced.
 */
const { t } = useI18n()
const route = useRoute()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

const code = computed(() => String(route.params.code ?? prefs.countryCode))

const indexResource = computed(() => data.indexByCountry[code.value] ?? null)
const indexPayload = computed(() => indexResource.value?.data ?? null)

const spilloverResource = computed(() => data.spilloverByCountry[code.value] ?? null)
const spillover = computed(() => spilloverResource.value?.data ?? null)

/**
 * The estimator the reader is looking at.
 *
 * The artefact publishes all of them side by side, because they answer
 * different questions and are not interchangeable — so the reader picks, and
 * the default is only the artefact's default.
 */
const estimator = ref<string>('')
const availableEstimators = computed(() => spillover.value?.availableMethods ?? [])
const selectedEstimator = computed({
  get: () => estimator.value || spillover.value?.defaultMethod || 'paper_equation',
  set: (value: string) => {
    estimator.value = value
    void data.loadSpillover(code.value, value)
  },
})

/**
 * The reason there is no network to show, when there is none.
 *
 * An economy measured by a published official index has no sub-market
 * decomposition by construction — that is a property of the economy, and it
 * must not be rendered as a failure.
 */
const spilloverEmptyMessage = computed(() => {
  const payload = spillover.value
  if (!payload || payload.available) {
    return null
  }
  return payload.unavailableReason === 'not_applicable'
    ? t('spillover.notAvailable')
    : t('spillover.unavailable')
})

const lensPoints = computed(() => {
  const payload = indexPayload.value
  if (!payload) {
    return []
  }
  return prefs.lens === 'percentile' ? payload.percentile : payload.deviation
})

const latestRegime = computed(() => indexPayload.value?.regime.points.at(-1) ?? null)

const regimeParams = computed(() => indexPayload.value?.regime.params ?? {})

function param(name: string, fallback: number): number {
  const value = regimeParams.value[name]
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

const regimeMechanism = computed(() => ({
  moderateMean: param('moderate_mean', 0),
  moderateStd: param('moderate_std', 0.2),
  highMean: param('high_mean', 0.5),
  highStd: param('high_std', 0.3),
  highWeight: latestRegime.value?.probabilityHigh ?? 0.5,
}))

const spilloverRows = computed(() => {
  const payload = spillover.value
  if (!payload) {
    return []
  }
  return payload.nodes.map((node) => ({
    node,
    label: labels.node(node),
    ownShare: payload.matrix[payload.nodes.indexOf(node)]?.[payload.nodes.indexOf(node)] ?? null,
    spillOut: payload.totalSpillout[node] ?? null,
    spillIn: payload.totalSpillin[node] ?? null,
    net: payload.net[node] ?? null,
  }))
})

watch(
  () => code.value,
  (value) => {
    prefs.setCountry(value)
    estimator.value = ''
    void data.loadIndex(value, prefs.lens)
    void data.loadSpillover(value)
  },
  { immediate: true },
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ labels.country(code) }}</h1>
        <p>{{ t('index.asOf', { date: format.date(indexPayload?.asOf ?? null) }) }}</p>
      </div>
      <RegimeBadge
        :regime="latestRegime?.regime ?? ''"
        :probability="latestRegime?.probabilityHigh ?? null"
      />
    </header>

    <DataState
      :status="indexResource?.status ?? 'idle'"
      :error="indexResource?.error ?? null"
      :empty="!indexPayload"
      @retry="data.loadIndex(code, prefs.lens)"
    >
      <div class="jd-stack">
        <section class="jd-panel">
          <h2>{{ labels.lens(prefs.lens) }}</h2>
          <CompositeChart :points="lensPoints" :lens="prefs.lens" />
        </section>

        <section class="jd-grid jd-grid-2">
          <div class="jd-panel">
            <h2>{{ t('regime.probability') }}</h2>
            <RegimeBandChart :points="indexPayload?.regime.points ?? []" />
          </div>
          <div class="jd-panel">
            <h2>{{ t('metric.sector') }}</h2>
            <MarketIndexChart :series="indexPayload?.marketIndices ?? []" />
          </div>
        </section>

        <section class="jd-panel">
          <h2>{{ t('common.regime') }}</h2>
          <RegimeMechanism
            :title="t('regime.probability')"
            :moderate-label="t('regime.moderate')"
            :high-label="t('regime.high')"
            :axis-label="t('index.composite')"
            :mixture-label="t('index.percentile')"
            :chain-label="`${t('regime.moderate')} / ${t('regime.high')}`"
            :moderate-mean="regimeMechanism.moderateMean"
            :moderate-std="regimeMechanism.moderateStd"
            :high-mean="regimeMechanism.highMean"
            :high-std="regimeMechanism.highStd"
            :high-weight="regimeMechanism.highWeight"
            :step-labels="[
              t('index.composite'),
              t('index.deviation'),
              t('index.percentile'),
              t('regime.probability'),
            ]"
            :result-labels="[t('regime.moderate'), t('regime.high')]"
          />
        </section>

        <section class="jd-panel">
          <div class="jd-row jd-row--spread">
            <h2>{{ t('nav.spillover') }}</h2>
            <el-select
              v-if="availableEstimators.length > 1"
              v-model="selectedEstimator"
              size="default"
              style="width: 280px"
              :aria-label="t('spillover.estimator')"
            >
              <el-option
                v-for="item in availableEstimators"
                :key="item"
                :label="labels.method(item)"
                :value="item"
              />
            </el-select>
          </div>
          <DataState
            :status="spilloverResource?.status ?? 'idle'"
            :error="spilloverResource?.error ?? null"
            :empty="!spillover || spillover.nodes.length === 0"
            :empty-message="spilloverEmptyMessage"
            @retry="data.loadSpillover(code)"
          >
            <el-table :data="spilloverRows" border stripe>
              <el-table-column :label="t('metric.sector')" min-width="160">
                <template #default="scope">{{ scope.row.label }}</template>
              </el-table-column>
              <el-table-column :label="t('metric.ownShare')" width="150" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.ownShare, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.spillOut')" width="150" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.spillOut, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.spillIn')" width="150" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.spillIn, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.net')" width="150" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.net, 2) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </DataState>
        </section>
      </div>
    </DataState>
  </div>
</template>
