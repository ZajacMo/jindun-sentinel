<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataState from '@/components/DataState.vue'
import SeverityBadge from '@/components/SeverityBadge.vue'
import AlertLoop from '@/components/diagrams/AlertLoop.vue'
import { usePrefsStore } from '@/stores/prefs'
import { useDataStore } from '@/stores/data'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import { SEVERITY_CODES } from '@/utils/codes'
import type { AlertPayload } from '@/api/types'

/**
 * The alerts.
 *
 * The fired rules of the selected economy, grouped by severity, together with
 * the mechanism diagram of the alerting loop they travel through.
 */
const { t } = useI18n()
const prefs = usePrefsStore()
const data = useDataStore()
const format = useFormat()
const labels = useLabels()

const resource = computed(() => data.alertsByCountry[prefs.countryCode] ?? null)
const alerts = computed(() => resource.value?.data ?? [])

/** The alerts of every severity, in the order P1, P2, P3. */
const grouped = computed(() =>
  SEVERITY_CODES.map((severity) => ({
    severity,
    label: labels.severity(severity),
    items: alerts.value.filter((alert) => alert.severity === severity),
  })),
)

/**
 * Render the message of an alert.
 *
 * The message key and its parameters come from the API; the parameters are
 * formatted with the active locale before they are interpolated.
 */
function message(alert: AlertPayload): string {
  if (!alert.messageKey) {
    return alert.ruleId
  }
  const params: Record<string, unknown> = { count: 1 }
  for (const [key, value] of Object.entries(alert.messageParams)) {
    if (typeof value === 'number') {
      params[key] = format.number(value, 4)
    } else if (typeof value === 'string') {
      params[key] = value
    }
  }
  if (alert.countryCode && !params.country) {
    params.country = labels.country(alert.countryCode)
  }
  return t(alert.messageKey, params)
}

onMounted(() => {
  void data.loadAlerts(prefs.countryCode)
})

watch(
  () => prefs.countryCode,
  () => {
    void data.loadAlerts(prefs.countryCode)
  },
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ t('nav.alerts') }}</h1>
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
      :empty="!resource?.data"
      @retry="data.loadAlerts(prefs.countryCode)"
    >
      <div class="jd-stack">
        <section v-for="group in grouped" :key="group.severity" class="jd-panel">
          <h2>
            <SeverityBadge :severity="group.severity" />
            <span class="jd-muted jd-count">{{ group.items.length }}</span>
          </h2>
          <el-table v-if="group.items.length > 0" :data="group.items" border>
            <el-table-column :label="t('nav.alerts')" min-width="300">
              <template #default="scope">{{ message(scope.row) }}</template>
            </el-table-column>
            <el-table-column :label="t('scope.country')" width="140">
              <template #default="scope">
                {{ labels.country(scope.row.countryCode) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('time.day')" width="190">
              <template #default="scope">
                {{ format.dateTime(scope.row.firedAt) }}
              </template>
            </el-table-column>
          </el-table>
          <p v-else class="jd-muted">{{ t('common.empty') }}</p>
        </section>

        <section class="jd-panel">
          <h2>{{ t('nav.alerts') }}</h2>
          <AlertLoop
            :title="t('nav.alerts')"
            :detect="t('nav.spillover')"
            :attribute="t('metric.sector')"
            :notify="t('nav.alerts')"
            :acknowledge="t('common.close')"
            :resolve="t('quality.ok')"
            :silence="t('time.day')"
            :loop-label="t('common.retry')"
          />
        </section>
      </div>
    </DataState>
  </div>
</template>

<style scoped>
.jd-count {
  margin-left: 8px;
  font-size: 0.9rem;
}
</style>
