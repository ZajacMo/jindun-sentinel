/**
 * A thin wrapper around ECharts.
 *
 * The chart instance is created on mount, updated whenever the option
 * changes, resized with the window and disposed on unmount.  Colours are read
 * from the CSS custom properties of the theme, so a chart follows the light and
 * the dark palette without any duplicated colour literals.
 */
import { onBeforeUnmount, onMounted, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'

/** Read a CSS custom property of the document root. */
export function cssVar(name: string, fallback = '#888888'): string {
  const value = globalThis
    .getComputedStyle?.(globalThis.document.documentElement)
    .getPropertyValue(name)
  return value && value.trim() ? value.trim() : fallback
}

/** The palette of the active theme, as ECharts colour values. */
export function themePalette() {
  return {
    accent: cssVar('--jd-accent'),
    accentSoft: cssVar('--jd-accent-soft'),
    high: cssVar('--jd-regime-high'),
    moderate: cssVar('--jd-regime-moderate'),
    muted: cssVar('--jd-text-muted'),
    grid: cssVar('--jd-chart-grid'),
    axis: cssVar('--jd-chart-axis'),
    surface: cssVar('--jd-surface'),
    text: cssVar('--jd-text'),
  }
}

/**
 * Bind an ECharts instance to a template element.
 *
 * The chart is created on mount, updated whenever the option changes, resized
 * with the window and disposed on unmount.
 */
export function useEChart(
  option: ComputedRef<EChartsOption>,
  element: Readonly<Ref<HTMLElement | null>>,
) {
  let chart: ECharts | null = null

  function render(): void {
    if (!element.value) {
      return
    }
    if (!chart) {
      // The SVG renderer is used on purpose: it needs no canvas context, it
      // inherits the CSS custom properties of the theme, and it keeps the
      // charts renderable in a non-browser environment such as jsdom.
      chart = echarts.init(element.value, undefined, { renderer: 'svg' })
    }
    chart.setOption(option.value, true)
  }

  function resize(): void {
    chart?.resize()
  }

  onMounted(() => {
    render()
    globalThis.addEventListener('resize', resize)
  })

  watch(option, () => render(), { deep: true })

  onBeforeUnmount(() => {
    globalThis.removeEventListener('resize', resize)
    chart?.dispose()
    chart = null
  })

  return { chart: () => chart }
}
