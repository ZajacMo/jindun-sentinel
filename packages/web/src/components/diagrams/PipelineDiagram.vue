<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The daily pipeline, drawn by hand.
 *
 * The diagram shows the whole chain a single observation travels through —
 * from the source, through the adapter and the quality gate, into the
 * normalised panel, the principal components and the composite index, on to
 * the regime model and the alerting rules, and finally out through the API
 * into the user interface.  The branch that leaves the quality gate is the
 * rejection path: a series that fails a gate is quarantined and never
 * reaches the index.
 */
export interface PipelineStage {
  label: string
  sub?: string
}

const props = defineProps<{
  title: string
  /** Ten stages, in the order they are executed. */
  stages: PipelineStage[]
  rejection: string
  rejectionNote?: string
}>()

const uid = useDiagramId('pipe')

const BOX_W = 170
const BOX_H = 64
const ROW_ONE_Y = 56
const ROW_TWO_Y = 262
const ROW_X = [40, 250, 460, 670, 880]
const REJECT_X = 460
const REJECT_Y = 152
const REJECT_W = 170
const REJECT_H = 56

/** Stages 0-4 run left to right, stages 5-9 continue right to left. */
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

/** Horizontal arrows inside a row; the second row runs right to left. */
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

/** The elbow that carries the flow from the end of the first row down. */
const turnArrow = computed(() => {
  const last = rowOne.value[rowOne.value.length - 1]
  const first = rowTwo.value[0]
  if (!last || !first) {
    return null
  }
  return {
    x: last.centreX,
    y1: last.y + BOX_H,
    y2: first.y,
  }
})

/** The rejection path that leaves the quality gate. */
const rejectionGate = computed(() => {
  const gate = placed.value[2]
  if (!gate) {
    return null
  }
  return {
    x: gate.centreX,
    y1: gate.y + BOX_H,
    y2: REJECT_Y,
  }
})

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const rejectHead = computed(() => `url(#${uid}-reject)`)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 400"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ stages.map((stage) => stage.label).join(' → ') }}. {{ rejection }}.
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
        :id="`${uid}-reject`"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="7"
        markerHeight="7"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--jd-diagram-reject)" />
      </marker>
    </defs>

    <text class="jd-diagram__title" x="40" y="26">{{ title }}</text>

    <!-- The main flow. -->
    <g>
      <template v-for="stage in placed" :key="`${stage.x}-${stage.y}`">
        <rect
          class="jd-node__box"
          :class="{
            'jd-node__box--accent': stage.row === 1 && stage.x === 880,
            'jd-node__box--reject': false,
          }"
          :x="stage.x"
          :y="stage.y"
          :width="BOX_W"
          :height="BOX_H"
          rx="8"
        />
        <text class="jd-node__label" :x="stage.centreX" :y="stage.centreY - (stage.sub ? 8 : 0)">
          {{ stage.label }}
        </text>
        <text v-if="stage.sub" class="jd-node__sub" :x="stage.centreX" :y="stage.centreY + 14">
          {{ stage.sub }}
        </text>
      </template>
    </g>

    <!-- Arrows between the stages of a row. -->
    <path
      v-for="(arrow, index) in rowArrows"
      :key="`row-arrow-${index}`"
      class="jd-arrow"
      :d="`M ${arrow.x1} ${arrow.y} L ${arrow.x2 - 6} ${arrow.y}`"
      :marker-end="arrowHead"
    />

    <!-- The elbow from the first row into the second. -->
    <path
      v-if="turnArrow"
      class="jd-arrow"
      :d="`M ${turnArrow.x} ${turnArrow.y1 + 4} L ${turnArrow.x} ${turnArrow.y2 - 6}`"
      :marker-end="arrowHead"
    />

    <!-- The rejection path of a failed quality gate. -->
    <g v-if="rejectionGate">
      <path
        class="jd-arrow jd-arrow--reject"
        :d="`M ${rejectionGate.x} ${rejectionGate.y1 + 4} L ${rejectionGate.x} ${rejectionGate.y2 - 6}`"
        :marker-end="rejectHead"
      />
      <rect
        class="jd-node__box jd-node__box--reject"
        :x="REJECT_X"
        :y="REJECT_Y"
        :width="REJECT_W"
        :height="REJECT_H"
        rx="8"
      />
      <text class="jd-node__label" :x="REJECT_X + REJECT_W / 2" :y="REJECT_Y + REJECT_H / 2 - 7">
        {{ rejection }}
      </text>
      <text
        v-if="rejectionNote"
        class="jd-node__sub"
        :x="REJECT_X + REJECT_W / 2"
        :y="REJECT_Y + REJECT_H / 2 + 14"
      >
        {{ rejectionNote }}
      </text>
    </g>
  </svg>
</template>
