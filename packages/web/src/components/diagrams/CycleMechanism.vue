<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * How the global financial cycle factor is produced.
 *
 * The diagram answers "where does this number come from": the three BIS
 * flows on the left are aligned to quarters and standardised, the first
 * principal component of that block is the factor in the middle, and the
 * country panel on the right is the independent check — a different object,
 * built from the monitored indices rather than from the BIS flows.
 */
export interface CycleFlow {
  code: string
  label: string
  series: string[]
}

const props = defineProps<{
  title: string
  flows: CycleFlow[]
  standardiseLabel: string
  componentLabel: string
  factorLabel: string
  crossCheckLabel: string
  countryPanelLabel: string
  note: string
}>()

const uid = useDiagramId('cycle')

const FLOW_X = 40
const FLOW_W = 300
const FLOW_H = 74
const FLOW_GAP = 26
const FLOW_Y = 92

const MID_X = 430
const MID_W = 250

const RIGHT_X = 770
const RIGHT_W = 390

const flows = computed(() =>
  props.flows.map((flow, index) => ({
    ...flow,
    y: FLOW_Y + index * (FLOW_H + FLOW_GAP),
  })),
)

const blockY = computed(() => FLOW_Y)
const blockH = computed(() => props.flows.length * (FLOW_H + FLOW_GAP) - FLOW_GAP)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 520"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ flows.map((flow) => `${flow.label}: ${flow.series.join(', ')}`).join('. ') }}.
      {{ standardiseLabel }}. {{ componentLabel }}. {{ factorLabel }}.
      {{ crossCheckLabel }}: {{ countryPanelLabel }}. {{ note }}
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

    <!-- The three BIS flows. -->
    <g v-for="flow in flows" :key="flow.code">
      <rect
        class="jd-node__box"
        :x="FLOW_X"
        :y="flow.y"
        :width="FLOW_W"
        :height="FLOW_H"
        rx="8"
      />
      <text class="jd-node__label" :x="FLOW_X + 14" :y="flow.y + 24">
        {{ flow.label }}
      </text>
      <text class="jd-diagram__small" :x="FLOW_X + 14" :y="flow.y + 44">
        {{ flow.series.join(' · ') }}
      </text>
    </g>

    <!-- The arrows from the flows into the standardised block. -->
    <path
      v-for="flow in flows"
      :key="`flow-arrow-${flow.code}`"
      class="jd-arrow"
      :d="`M ${FLOW_X + FLOW_W} ${flow.y + FLOW_H / 2} L ${MID_X - 12} ${flow.y + FLOW_H / 2} L ${MID_X} ${blockY + blockH / 2}`"
      :marker-end="`url(#${uid}-arrow)`"
    />

    <!-- The standardised block and the principal component. -->
    <rect
      class="jd-node__box jd-node__box--accent"
      :x="MID_X"
      :y="blockY"
      :width="MID_W"
      :height="blockH"
      rx="8"
    />
    <text class="jd-node__label" :x="MID_X + 16" :y="blockY + 26">
      {{ standardiseLabel }}
    </text>
    <text class="jd-diagram__small" :x="MID_X + 16" :y="blockY + 50">
      {{ componentLabel }}
    </text>

    <path
      class="jd-arrow jd-arrow--accent"
      :d="`M ${MID_X + MID_W} ${blockY + blockH / 2} L ${RIGHT_X - 12} ${blockY + blockH / 2}`"
      :marker-end="`url(#${uid}-accent)`"
    />

    <!-- The factor itself. -->
    <rect
      class="jd-node__box jd-node__box--accent"
      :x="RIGHT_X"
      :y="blockY"
      :width="RIGHT_W"
      :height="118"
      rx="8"
    />
    <text class="jd-node__label" :x="RIGHT_X + 16" :y="blockY + 26">
      {{ factorLabel }}
    </text>
    <text class="jd-diagram__small" :x="RIGHT_X + 16" :y="blockY + 50">
      {{ note }}
    </text>

    <!-- The independent cross-check. -->
    <rect
      class="jd-node__box"
      :x="RIGHT_X"
      :y="blockY + 146"
      :width="RIGHT_W"
      :height="118"
      rx="8"
    />
    <text class="jd-node__label" :x="RIGHT_X + 16" :y="blockY + 172">
      {{ crossCheckLabel }}
    </text>
    <text class="jd-diagram__small" :x="RIGHT_X + 16" :y="blockY + 196">
      {{ countryPanelLabel }}
    </text>
  </svg>
</template>
