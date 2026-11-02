<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { SortDown, SortUp } from '@element-plus/icons-vue'
import DataState from '@/components/DataState.vue'
import SpilloverNetwork from '@/components/charts/SpilloverNetwork.vue'
import GlobalNetwork from '@/components/diagrams/GlobalNetwork.vue'
import SpilloverMechanism from '@/components/diagrams/SpilloverMechanism.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import type { SpilloverPayload } from '@/api/types'

/**
 * The contagion network.
 *
 * The spillover matrix of the cross-country layer and of the cross-market
 * layer of the selected economy, drawn as a chord diagram and listed as a
 * sortable matrix with the spill-out, spill-in and net columns.
 */
const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

type ScopeName = 'global' | 'country'

/** Proper nouns are not translated. */
const ECB_CISS = 'ECB CISS'
const BIS = 'BIS'

const scope = ref<ScopeName>('global')
const sortBy = ref<string>('spillOut')
const sortOrder = ref<'ascending' | 'descending'>('descending')

/**
 * The estimator the reader is looking at.
 *
 * The artefacts publish all of them side by side, because they answer
 * different questions and are not interchangeable — so the reader picks, and
 * the default is only the artefact's default.
 */
const estimator = ref<string>('')

const globalResource = computed(() => data.globalSpillover)
const countryResource = computed(() => data.spilloverByCountry[prefs.countryCode] ?? null)

const activeResource = computed(() =>
  scope.value === 'global' ? globalResource.value : countryResource.value,
)

const payload = computed<SpilloverPayload | null>(() => activeResource.value?.data ?? null)

const availableEstimators = computed(() => payload.value?.availableMethods ?? [])

const selectedEstimator = computed({
  get: () => estimator.value || payload.value?.defaultMethod || 'paper_equation',
  set: (value: string) => {
    estimator.value = value
    reload()
  },
})

/**
 * The reason there is no network to show, when there is none.  An economy
 * measured by a published official index has no sub-market decomposition by
 * construction — that is a property of the economy, not a failure.
 */
const spilloverEmptyMessage = computed(() => {
  const current = payload.value
  if (!current || current.available) {
    return null
  }
  return current.unavailableReason === 'not_applicable'
    ? t('spillover.notAvailable')
    : t('spillover.unavailable')
})

const nodes = computed(() => payload.value?.nodes ?? [])
const matrix = computed(() => payload.value?.matrix ?? [])

const rows = computed(() => {
  const current = payload.value
  if (!current) {
    return []
  }
  return current.nodes.map((node, index) => ({
    node,
    label: labels.node(node),
    ownShare: current.matrix[index]?.[index] ?? null,
    spillOut: current.totalSpillout[node] ?? null,
    spillIn: current.totalSpillin[node] ?? null,
    net: current.net[node] ?? null,
  }))
})

const sortedRows = computed(() => {
  const copy = [...rows.value]
  const key = sortBy.value as keyof (typeof copy)[number]
  copy.sort((left, right) => {
    const a = left[key]
    const b = right[key]
    const leftValue = typeof a === 'number' ? a : 0
    const rightValue = typeof b === 'number' ? b : 0
    return sortOrder.value === 'ascending'
      ? leftValue - rightValue
      : rightValue - leftValue
  })
  return copy
})

/** The markets of the contagion mechanism diagram. */
const marketList = computed(() =>
  ['equity', 'bond', 'fx', 'money', 'derivative'].map((code) => ({
    code,
    label: labels.market(code),
  })),
)

/**
 * The nodes the contagion mechanism diagram draws.
 *
 * They follow the network that is actually on screen: the markets of the
 * selected economy, or the countries of the global layer.  Drawing the five
 * Chinese sub-markets while the table above lists five countries would show
 * a mechanism that does not belong to the numbers.
 */
const mechanismMarkets = computed(() => {
  const nodes = payload.value?.nodes ?? []
  if (nodes.length > 0) {
    const list = nodes.map((code) => ({ code, label: labels.node(code) }))
    return {
      shock: list[0] ?? { code: 'equity', label: labels.market('equity') },
      others: list.slice(1),
    }
  }
  const fallback = marketList.value
  return {
    shock: fallback[0] ?? { code: 'equity', label: labels.market('equity') },
    others: fallback.slice(1),
  }
})

const globalCountries = computed(() =>
  ['CN', 'US', 'EU', 'GB', 'JP'].map((code) => ({
    code,
    label: labels.country(code),
  })),
)

const anchorCountry = computed(() => {
  const countries = data.countries.data ?? []
  const anchored = countries.find((country) => country.cissArea)
  return anchored?.code ?? 'EU'
})

function reload(): void {
  const method = estimator.value || 'paper_equation'
  if (scope.value === 'global') {
    void data.loadGlobalSpillover(method)
  } else {
    void data.loadSpillover(prefs.countryCode, method)
  }
}

onMounted(reload)
watch(scope, () => {
  // Each scope publishes its own set of estimators, so the selection starts
  // again from that artefact's default.
  estimator.value = ''
  reload()
})
watch(
  () => prefs.countryCode,
  () => {
    if (scope.value === 'country') {
      estimator.value = ''
      reload()
    }
  },
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ t('nav.spillover') }}</h1>
        <p>{{ payload ? labels.method(payload.method) : '' }}</p>
      </div>
      <div class="jd-row">
        <el-radio-group v-model="scope" size="default">
          <el-radio-button value="global">{{ t('scope.global') }}</el-radio-button>
          <el-radio-button value="country">{{ t('scope.country') }}</el-radio-button>
        </el-radio-group>
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
        <el-select v-model="sortBy" size="default" style="width: 170px">
          <el-option :label="t('metric.spillOut')" value="spillOut" />
          <el-option :label="t('metric.spillIn')" value="spillIn" />
          <el-option :label="t('metric.net')" value="net" />
          <el-option :label="t('metric.ownShare')" value="ownShare" />
        </el-select>
        <el-button
          size="default"
          :aria-label="t('metric.spillOut')"
          :icon="sortOrder === 'ascending' ? SortUp : SortDown"
          @click="sortOrder = sortOrder === 'ascending' ? 'descending' : 'ascending'"
        />
      </div>
    </header>

    <DataState
      :status="activeResource?.status ?? 'idle'"
      :error="activeResource?.error ?? null"
      :empty="!payload || payload.nodes.length === 0"
      :empty-message="spilloverEmptyMessage"
      @retry="reload"
    >
      <div class="jd-stack">
        <section v-if="payload && payload.notes.length > 0" class="jd-panel">
          <h2>{{ t('common.notes') }}</h2>
          <ul class="jd-notes">
            <li v-for="(note, index) in payload.notes" :key="index">{{ note }}</li>
          </ul>
        </section>

        <section class="jd-grid jd-grid-2">
          <div class="jd-panel">
            <h2>{{ t('nav.spillover') }}</h2>
            <SpilloverNetwork :nodes="nodes" :matrix="matrix" :title="t('nav.spillover')" />
          </div>
          <div class="jd-panel">
            <h2>{{ t('metric.sector') }}</h2>
            <el-table :data="sortedRows" border stripe>
              <el-table-column :label="t('metric.sector')" min-width="150">
                <template #default="scope">{{ scope.row.label }}</template>
              </el-table-column>
              <el-table-column :label="t('metric.ownShare')" width="140" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.ownShare, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.spillOut')" width="140" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.spillOut, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.spillIn')" width="140" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.spillIn, 2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('metric.net')" width="140" class-name="jd-numeric">
                <template #default="scope">
                  <span class="jd-numeric">{{ format.percent(scope.row.net, 2) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </section>

        <section class="jd-panel">
          <h2>{{ labels.method(payload?.method ?? 'paper_equation') }}</h2>
          <SpilloverMechanism
            :title="t('nav.spillover')"
            :shock="mechanismMarkets.shock"
            :others="mechanismMarkets.others"
            :shock-label="t('common.source')"
            :response-label="t('spillover.impulseResponses')"
            :horizon-label="t('time.day')"
            :share-label="t('metric.ownShare')"
            :variance-label="t('metric.spillIn')"
            :feedback-label="t('nav.spillover')"
            :horizon="payload?.horizon ?? 10"
          />
        </section>

        <section class="jd-panel">
          <h2>{{ t('scope.global') }}</h2>
          <GlobalNetwork
            :title="t('scope.global')"
            :countries="globalCountries"
            :layers="marketList.map((market) => market.label)"
            :anchor-country="anchorCountry"
            :anchor-label="ECB_CISS"
            :bis-label="BIS"
            :layers-label="t('metric.sector')"
          />
        </section>
      </div>
    </DataState>
  </div>
</template>

<style scoped>
.jd-notes {
  margin: 0;
  padding-left: 1.2em;
}
</style>
