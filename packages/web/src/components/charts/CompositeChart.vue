<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import type { EChartsOption } from 'echarts'
import { useEChart, themePalette } from '@/composables/useEChart'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import type { SeriesPoint } from '@/api/types'

/**
 * The composite stress index as a time series.
 *
 * The two reporting lenses are drawn on the same axis because they share the
 * same unit — the within-country percentile and the distance from the
 * country's own trend.
 */
const props = defineProps<{
  points: SeriesPoint[]
  lens: 'percentile' | 'deviation'
}>()

const format = useFormat()
const labels = useLabels()

const option = computed<EChartsOption>(() => {
  const palette = themePalette()
  const dates = props.points.map((point) => point.date)
  const values = props.points.map((point) => point.value)
  const seriesName = labels.lens(props.lens)
  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 28, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => format.number(Number(value), 4),
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
      scale: true,
      splitLine: { lineStyle: { color: palette.grid } },
      axisLabel: { color: palette.muted },
    },
    series: [
      {
        name: seriesName,
        type: 'line',
        smooth: false,
        showSymbol: false,
        sampling: 'lttb',
        data: values,
        lineStyle: { color: palette.accent, width: 1.8 },
        itemStyle: { color: palette.accent },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: palette.accentSoft },
              { offset: 1, color: 'transparent' },
            ],
          },
        },
      },
    ],
  }
})

const element = useTemplateRef<HTMLElement>('chartElement')
useEChart(option, element)
</script>

<template>
  <div ref="chartElement" class="jd-chart" role="img" :aria-label="labels.lens(lens)" />
</template>
