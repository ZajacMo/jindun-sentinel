<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import type { EChartsOption } from 'echarts'
import { useEChart, themePalette } from '@/composables/useEChart'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import type { RegimePoint } from '@/api/types'

/**
 * The regime probability band.
 *
 * The two components of the mixture are stacked, so the band between them is
 * the probability of the high-stress state; the markers show the state the
 * model actually assigned to each observation.
 */
const props = defineProps<{ points: RegimePoint[] }>()

const format = useFormat()
const labels = useLabels()

const option = computed<EChartsOption>(() => {
  const palette = themePalette()
  const dates = props.points.map((point) => point.date)
  const moderate = props.points.map((point) => point.probabilityModerate)
  const high = props.points.map((point) => point.probabilityHigh)
  const regimes = props.points.map((point) => point.regime)

  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 28, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => format.percent(Number(value)),
    },
    legend: {
      data: [labels.regime('moderate'), labels.regime('high')],
      textStyle: { color: palette.muted },
      top: 0,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: palette.axis } },
      axisLabel: { color: palette.muted, hideOverlap: true },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { color: palette.muted, formatter: (value: number) => format.percent(value, 0) },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [
      {
        name: labels.regime('moderate'),
        type: 'line',
        stack: 'probability',
        areaStyle: { color: palette.moderate },
        lineStyle: { width: 0 },
        symbol: 'none',
        data: moderate,
      },
      {
        name: labels.regime('high'),
        type: 'line',
        stack: 'probability',
        areaStyle: { color: palette.high },
        lineStyle: { width: 0 },
        symbol: 'none',
        data: high,
      },
      {
        name: labels.regime('high'),
        type: 'line',
        lineStyle: { color: palette.high, width: 1.4, type: 'dashed' },
        symbol: 'none',
        data: regimes.map((regime) => (regime === 'high' ? 1 : null)),
      },
    ],
  }
})

const element = useTemplateRef<HTMLElement>('chartElement')
useEChart(option, element)
</script>

<template>
  <div ref="chartElement" class="jd-chart" role="img" :aria-label="labels.regime('probability')" />
</template>
