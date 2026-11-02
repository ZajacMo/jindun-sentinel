<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import type { EChartsOption } from 'echarts'
import { useEChart, themePalette } from '@/composables/useEChart'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'
import type { MarketIndexSeries } from '@/api/types'

/**
 * The five market indices of one economy on a shared axis.
 *
 * The markets do not share the same history — an equity index usually starts
 * earlier than a money-market series — so the axis is the union of all their
 * dates and every series is aligned to it by date, not by position.
 */
const props = defineProps<{ series: MarketIndexSeries[] }>()

const format = useFormat()
const labels = useLabels()

const palette = [
  '#0f766e',
  '#b3261e',
  '#9a5b00',
  '#3d5878',
  '#7a4f9c',
  '#1f6f43',
]

/** The union of all observation dates, in chronological order. */
const dates = computed(() => {
  const all = new Set<string>()
  for (const item of props.series) {
    for (const point of item.points) {
      all.add(point.date)
    }
  }
  return [...all].sort()
})

const option = computed<EChartsOption>(() => {
  const theme = themePalette()
  const axis = dates.value
  return {
    backgroundColor: 'transparent',
    grid: { left: 52, right: 20, top: 28, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => format.number(Number(value), 4),
    },
    legend: {
      data: props.series.map((item) => labels.market(item.code)),
      textStyle: { color: theme.muted },
      top: 0,
    },
    xAxis: {
      type: 'category',
      data: axis,
      axisLine: { lineStyle: { color: theme.axis } },
      axisLabel: { color: theme.muted, hideOverlap: true },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: theme.grid } },
      axisLabel: { color: theme.muted },
    },
    series: props.series.map((item, index) => {
      const byDate = new Map(item.points.map((point) => [point.date, point.value]))
      return {
        name: labels.market(item.code),
        type: 'line' as const,
        showSymbol: false,
        sampling: 'lttb',
        connectNulls: false,
        data: axis.map((date) => byDate.get(date) ?? null),
        lineStyle: { color: palette[index % palette.length], width: 1.6 },
        itemStyle: { color: palette[index % palette.length] },
      }
    }),
  }
})

const element = useTemplateRef<HTMLElement>('chartElement')
useEChart(option, element)
</script>

<template>
  <div ref="chartElement" class="jd-chart" role="img" :aria-label="labels.t('index.composite')" />
</template>
