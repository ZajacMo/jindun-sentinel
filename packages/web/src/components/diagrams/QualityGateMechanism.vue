<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The data-quality gate.
 *
 * Every fetched series is put through the same set of named checks.  A series
 * that is merely stale or incomplete earns a warning and is still published;
 * a series that is broken fails the gate and is blocked, so no index is ever
 * built on top of it.
 */
const props = defineProps<{
  title: string
  source: string
  /** The names of the individual checks. */
  checks: string[]
  verdict: string
  publish: string
  block: string
}>()

const uid = useDiagramId('quality')

const SOURCE_X = 30
const SOURCE_W = 150
const SOURCE_H = 60

const CHECK_X = 230
const CHECK_W = 220
const CHECK_H = 46
const CHECK_GAP_X = 30
const CHECK_GAP_Y = 18
const CHECK_TOP = 60

const VERDICT_X = 780
const VERDICT_W = 160
const VERDICT_Y = 170

const placed = computed(() =>
  props.checks.map((label, index) => {
    const column = index % 2
    const row = Math.floor(index / 2)
    const x = CHECK_X + column * (CHECK_W + CHECK_GAP_X)
    const y = CHECK_TOP + row * (CHECK_H + CHECK_GAP_Y)
    return { label, x, y, centreX: x + CHECK_W / 2, centreY: y + CHECK_H / 2 }
  }),
)

/** The block of checks, and the source that feeds it. */
const layout = computed(() => {
  const list = placed.value
  const first = list[0]
  const last = list[list.length - 1]
  const top = first ? first.y : CHECK_TOP
  const bottom = last ? last.y + CHECK_H : CHECK_TOP + CHECK_H
  const midY = first && last ? (first.centreY + last.centreY) / 2 : CHECK_TOP
  return {
    sourceY: (top + bottom) / 2 - SOURCE_H / 2,
    checksRight: CHECK_X + CHECK_W + CHECK_GAP_X + CHECK_W,
    checksMidY: midY,
  }
})

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const accentHead = computed(() => `url(#${uid}-accent)`)
const rejectHead = computed(() => `url(#${uid}-reject)`)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 420"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ source }} → {{ checks.join(', ') }} → {{ verdict }} → {{ publish }} / {{ block }}
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

    <text class="jd-diagram__title" x="30" y="26">{{ title }}</text>

    <!-- The fetched series. -->
    <rect
      class="jd-node__box"
      :x="SOURCE_X"
      :y="layout.sourceY"
      :width="SOURCE_W"
      :height="SOURCE_H"
      rx="8"
    />
    <text
      class="jd-node__label"
      :x="SOURCE_X + SOURCE_W / 2"
      :y="layout.sourceY + SOURCE_H / 2 + 5"
    >
      {{ source }}
    </text>

    <!-- The individual checks. -->
    <g v-for="(check, index) in placed" :key="`check-${index}`">
      <rect
        class="jd-node__box"
        :x="check.x"
        :y="check.y"
        :width="CHECK_W"
        :height="CHECK_H"
        rx="8"
      />
      <text class="jd-node__label" :x="check.centreX" :y="check.centreY + 4">
        {{ check.label }}
      </text>
    </g>

    <!-- The source feeds the checks. -->
    <path
      class="jd-arrow"
      :d="`M ${SOURCE_X + SOURCE_W + 8} ${layout.sourceY + SOURCE_H / 2} L ${CHECK_X - 12} ${layout.sourceY + SOURCE_H / 2}`"
      :marker-end="arrowHead"
    />

    <!-- The checks feed the verdict. -->
    <path
      class="jd-arrow"
      :d="`M ${layout.checksRight + 8} ${layout.checksMidY} L ${VERDICT_X - 10} ${VERDICT_Y + 30}`"
      :marker-end="arrowHead"
    />

    <!-- The verdict. -->
    <rect
      class="jd-node__box jd-node__box--accent"
      :x="VERDICT_X"
      :y="VERDICT_Y"
      :width="VERDICT_W"
      height="60"
      rx="8"
    />
    <text class="jd-node__label" :x="VERDICT_X + VERDICT_W / 2" :y="VERDICT_Y + 30 + 5">
      {{ verdict }}
    </text>

    <!-- The two outcomes. -->
    <rect
      class="jd-node__box jd-node__box--accent"
      x="980"
      y="120"
      width="190"
      height="52"
      rx="8"
    />
    <text class="jd-node__label" x="1075" y="150">{{ publish }}</text>
    <rect
      class="jd-node__box jd-node__box--reject"
      x="980"
      y="220"
      width="190"
      height="52"
      rx="8"
    />
    <text class="jd-node__label" x="1075" y="250">{{ block }}</text>

    <path
      class="jd-arrow jd-arrow--accent"
      d="M 940 190 C 970 190 960 146 978 146"
      :marker-end="accentHead"
    />
    <path
      class="jd-arrow jd-arrow--reject"
      d="M 940 210 C 970 210 960 246 978 246"
      :marker-end="rejectHead"
    />
  </svg>
</template>
