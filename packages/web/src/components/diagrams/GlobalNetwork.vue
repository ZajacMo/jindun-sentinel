<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The global layer.
 *
 * The five monitored economies are drawn as columns; each column stacks the
 * five market layers that the country index is built from.  Where the ECB
 * publishes a CISS index for an area, that index is anchored next to the
 * economy as an independent systemic-stress reference, and the BIS
 * cross-border banking statistics are drawn as the edges that connect the
 * economies to each other.
 */
export interface NetworkCountry {
  code: string
  label: string
}

const props = defineProps<{
  title: string
  countries: NetworkCountry[]
  /** The five market layers of every economy. */
  layers: string[]
  /** The country the ECB CISS anchor belongs to, when there is one. */
  anchorCountry?: string
  anchorLabel: string
  bisLabel: string
  layersLabel: string
}>()

const uid = useDiagramId('global')

const COLUMN_W = 180
const COLUMN_GAP = 55
const COUNTRY_Y = 110
const COUNTRY_H = 56
const LAYER_TOP = 208
const LAYER_H = 28
const LAYER_GAP = 8

const columns = computed(() =>
  props.countries.map((country, index) => ({
    ...country,
    x: 40 + index * (COLUMN_W + COLUMN_GAP),
  })),
)

/** The cross-border banking edges between the economies. */
const edges = computed(() => {
  const list = columns.value
  const result: { d: string; labelX: number; labelY: number }[] = []
  for (let index = 0; index < list.length - 1; index += 1) {
    const from = list[index] as (typeof list)[number]
    const to = list[index + 1] as (typeof list)[number]
    const startX = from.x + COLUMN_W
    const endX = to.x
    const midX = (startX + endX) / 2
    result.push({
      d: `M ${startX} ${COUNTRY_Y + COUNTRY_H / 2} Q ${midX} ${COUNTRY_Y - 46} ${endX} ${COUNTRY_Y + COUNTRY_H / 2}`,
      labelX: midX,
      labelY: COUNTRY_Y - 34,
    })
  }
  return result
})

const anchor = computed(() => {
  if (!props.anchorCountry) {
    return null
  }
  const column = columns.value.find((item) => item.code === props.anchorCountry)
  if (!column) {
    return null
  }
  return {
    x: column.x + COLUMN_W + 38,
    y: COUNTRY_Y + COUNTRY_H / 2,
    radius: 30,
    lineX1: column.x + COLUMN_W,
    lineX2: column.x + COLUMN_W + 38 - 30,
  }
})

const accentHead = computed(() => `url(#${uid}-accent)`)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 540"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ countries.map((country) => country.label).join(', ') }}. {{ layersLabel }}:
      {{ layers.join(', ') }}. {{ bisLabel }}. {{ anchorLabel }}.
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

    <text class="jd-diagram__title" x="30" y="24">{{ title }}</text>

    <!-- The cross-border banking edges. -->
    <g>
      <path
        v-for="(edge, index) in edges"
        :key="`edge-${index}`"
        class="jd-arrow jd-arrow--accent"
        :d="edge.d"
        :marker-end="accentHead"
      />
      <text
        v-for="(edge, index) in edges"
        :key="`edge-label-${index}`"
        class="jd-diagram__small"
        :x="edge.labelX"
        :y="edge.labelY"
        text-anchor="middle"
      >
        {{ bisLabel }}
      </text>
    </g>

    <!-- The economies and their market layers. -->
    <g v-for="column in columns" :key="column.code">
      <rect
        class="jd-node__box jd-node__box--accent"
        :x="column.x"
        :y="COUNTRY_Y"
        :width="COLUMN_W"
        :height="COUNTRY_H"
        rx="8"
      />
      <text
        class="jd-node__label"
        :x="column.x + COLUMN_W / 2"
        :y="COUNTRY_Y + COUNTRY_H / 2 + 5"
      >
        {{ column.label }}
      </text>

      <g v-for="(layer, index) in layers" :key="`${column.code}-${index}`">
        <rect
          class="jd-node__box"
          :x="column.x"
          :y="LAYER_TOP + index * (LAYER_H + LAYER_GAP)"
          :width="COLUMN_W"
          :height="LAYER_H"
          rx="6"
        />
        <text
          class="jd-diagram__small"
          :x="column.x + 10"
          :y="LAYER_TOP + index * (LAYER_H + LAYER_GAP) + LAYER_H / 2 + 4"
        >
          {{ layer }}
        </text>
      </g>
    </g>

    <!-- The ECB CISS anchor. -->
    <g v-if="anchor">
      <path
        class="jd-arrow jd-arrow--muted"
        :d="`M ${anchor.lineX1} ${anchor.y} L ${anchor.lineX2} ${anchor.y}`"
      />
      <circle
        class="jd-node__box jd-node__box--accent"
        :cx="anchor.x"
        :cy="anchor.y"
        :r="anchor.radius"
      />
      <text
        class="jd-diagram__small"
        :x="anchor.x"
        :y="anchor.y + 4"
        text-anchor="middle"
      >
        {{ anchorLabel }}
      </text>
    </g>

    <text class="jd-diagram__small" x="40" y="500">{{ layersLabel }}</text>
  </svg>
</template>
