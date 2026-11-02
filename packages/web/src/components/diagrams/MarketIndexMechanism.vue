<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * How a market index is built.
 *
 * The tertiary indicators of one market are mapped onto their own empirical
 * distribution, reduced to the principal components that explain enough of
 * the variance, weighted with the CRITIC weights, and finally combined with
 * the market weights into the composite index.
 */
export interface IndexStage {
  label: string
  sub?: string
}

const props = defineProps<{
  title: string
  stages: IndexStage[]
  composite: string
}>()

const uid = useDiagramId('index')

const BOX_W = 190
const BOX_H = 64
const ROW_ONE_Y = 54
const ROW_TWO_Y = 250
const ROW_X = [40, 270, 500, 730, 960]

const placed = computed(() =>
  props.stages.map((stage, index) => {
    const row = index < 5 ? 0 : 1
    const column = index < 5 ? index : 9 - index
    const x = ROW_X[column] as number
    const y = row === 0 ? ROW_ONE_Y : ROW_TWO_Y
    return {
      ...stage,
      x,
      y,
      centreX: x + BOX_W / 2,
      centreY: y + BOX_H / 2,
      row,
    }
  }),
)

const rowOne = computed(() => placed.value.filter((stage) => stage.row === 0))
const rowTwo = computed(() => placed.value.filter((stage) => stage.row === 1))

const rowArrows = computed(() => {
  const arrows: { x1: number; y: number; x2: number }[] = []
  for (let index = 0; index < rowOne.value.length - 1; index += 1) {
    const from = rowOne.value[index] as (typeof rowOne.value)[number]
    const to = rowOne.value[index + 1] as (typeof rowOne.value)[number]
    arrows.push({ x1: from.x + BOX_W, y: from.centreY, x2: to.x })
  }
  for (let index = 0; index < rowTwo.value.length - 1; index += 1) {
    const from = rowTwo.value[index] as (typeof rowTwo.value)[number]
    const to = rowTwo.value[index + 1] as (typeof rowTwo.value)[number]
    arrows.push({ x1: from.x, y: from.centreY, x2: to.x + BOX_W })
  }
  return arrows
})

const turnArrow = computed(() => {
  const last = rowOne.value[rowOne.value.length - 1]
  const first = rowTwo.value[0]
  if (!last || !first) {
    return null
  }
  return { x: last.centreX, y1: last.y + BOX_H, y2: first.y }
})

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const accentHead = computed(() => `url(#${uid}-accent)`)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 380"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ stages.map((stage) => stage.label).join(' → ') }} → {{ composite }}
    </desc>

    <defs>
      <marker
        :id="`${uid}-arrow`"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="7"
        markerHeight="7"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--jd-diagram-line)" />
      </marker>
      <marker
        :id="`${uid}-accent`"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="7"
        markerHeight="7"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--jd-diagram-accent)" />
      </marker>
    </defs>

    <text class="jd-diagram__title" x="40" y="26">{{ title }}</text>

    <template v-for="stage in placed" :key="`${stage.x}-${stage.y}`">
      <rect
        class="jd-node__box"
        :class="{ 'jd-node__box--accent': stage.row === 1 && stage.x === 500 }"
        :x="stage.x"
        :y="stage.y"
        :width="BOX_W"
        :height="BOX_H"
        rx="8"
      />
      <text class="jd-node__label" :x="stage.centreX" :y="stage.centreY - (stage.sub ? 8 : 0)">
        {{ stage.label }}
      </text>
      <text v-if="stage.sub" class="jd-node__sub" :x="stage.centreX" :y="stage.centreY + 15">
        {{ stage.sub }}
      </text>
    </template>

    <path
      v-for="(arrow, index) in rowArrows"
      :key="`arrow-${index}`"
      class="jd-arrow"
      :d="`M ${arrow.x1} ${arrow.y} L ${arrow.x2 - 6} ${arrow.y}`"
      :marker-end="arrowHead"
    />

    <path
      v-if="turnArrow"
      class="jd-arrow jd-arrow--accent"
      :d="`M ${turnArrow.x} ${turnArrow.y1 + 4} L ${turnArrow.x} ${turnArrow.y2 - 6}`"
      :marker-end="accentHead"
    />
  </svg>
</template>
