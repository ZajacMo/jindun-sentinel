<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import type { EChartsOption } from 'echarts'
import { useEChart, themePalette } from '@/composables/useEChart'
import { useFormat } from '@/composables/useFormat'

/**
 * The global financial cycle factor as a time series.
 *
 * The factor is quarterly, so the chart has far fewer points than the daily
 * country indices next to it.  The zero line is drawn explicitly: the factor
 * is a centred quantity, and a reader has to be able to see which side of
 * the average the current quarter sits on.
 */
const props = defineProps<{
  dates: string[]
  factor: number[]
  title: string
}>()

const format = useFormat()

const option = computed<EChartsOption>(() => {
  const palette = themePalette()
  return {
    backgroundColor: 'transparent',
    grid: { left: 56, right: 24, top: 28, bottom: 44 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => format.number(Number(value), 3),
    },
    xAxis: {
      type: 'category',
      data: props.dates,
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
        name: props.title,
        type: 'line',
        smooth: false,
        showSymbol: false,
        data: props.factor,
        lineStyle: { color: palette.accent, width: 1.8 },
        itemStyle: { color: palette.accent },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: palette.muted, type: 'dashed', width: 1 },
          data: [{ yAxis: 0 }],
          label: { show: false },
        },
      },
    ],
  }
})

const element = useTemplateRef<HTMLElement>('chartElement')
useEChart(option, element)
</script>

<template>
  <div ref="chartElement" class="jd-chart" role="img" :aria-label="title" />
</template>
