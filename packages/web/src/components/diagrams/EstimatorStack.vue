<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The estimator stack.
 *
 * All four spillover estimators read from the same VAR model and the same
 * VMA coefficients, and they all report under the same convention: a
 * row-normalised share matrix.  They are not interchangeable, and the diagram
 * makes that explicit by showing them as parallel branches.
 */
export interface EstimatorEntry {
  code: string
  label: string
  note?: string
}

const props = defineProps<{
  title: string
  model: string
  vma: string
  decomposition: string
  estimators: EstimatorEntry[]
  convention: string
  conventionNote?: string
}>()

const uid = useDiagramId('est')

const ROW_ONE_Y = 50
const ROW_ONE_H = 56
const ROW_ONE_X = [120, 460, 800]
const ROW_ONE_W = 280

const BUS_Y = 150

const METHOD_Y = 190
const METHOD_W = 250
const METHOD_H = 64
const METHOD_X = [60, 345, 630, 915]

const CONVENTION_Y = 300
const CONVENTION_H = 56

const rowOne = computed(() =>
  ([props.model, props.vma, props.decomposition] as string[]).map((label, index) => ({
    label,
    x: ROW_ONE_X[index] as number,
    centreX: (ROW_ONE_X[index] as number) + ROW_ONE_W / 2,
  })),
)

const methods = computed(() =>
  props.estimators.map((entry, index) => ({
    ...entry,
    x: METHOD_X[index % METHOD_X.length] as number,
    centreX: (METHOD_X[index % METHOD_X.length] as number) + METHOD_W / 2,
  })),
)

const busStart = computed(() => methods.value[0]?.centreX ?? 185)
const busEnd = computed(() => methods.value[methods.value.length - 1]?.centreX ?? 1040)

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
      {{ model }} → {{ vma }} → {{ decomposition }} →
      {{ estimators.map((entry) => entry.label).join(', ') }} → {{ convention }}
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

    <!-- The shared inputs. -->
    <g v-for="(entry, index) in rowOne" :key="`input-${index}`">
      <rect
        class="jd-node__box"
        :x="entry.x"
        :y="ROW_ONE_Y"
        :width="ROW_ONE_W"
        :height="ROW_ONE_H"
        rx="8"
      />
      <text class="jd-node__label" :x="entry.centreX" :y="ROW_ONE_Y + ROW_ONE_H / 2 + 5">
        {{ entry.label }}
      </text>
      <path
        v-if="index < rowOne.length - 1"
        class="jd-arrow"
        :d="`M ${entry.x + ROW_ONE_W + 8} ${ROW_ONE_Y + ROW_ONE_H / 2} L ${(rowOne[index + 1]?.x ?? 0) - 10} ${ROW_ONE_Y + ROW_ONE_H / 2}`"
        :marker-end="arrowHead"
      />
      <path
        class="jd-arrow jd-arrow--muted"
        :d="`M ${entry.centreX} ${ROW_ONE_Y + ROW_ONE_H + 4} L ${entry.centreX} ${BUS_Y}`"
      />
    </g>

    <!-- The bus that feeds the estimators. -->
    <path
      class="jd-flow"
      :d="`M ${busStart} ${BUS_Y} L ${busEnd} ${BUS_Y}`"
    />

    <!-- The four estimators. -->
    <g v-for="(entry, index) in methods" :key="entry.code">
      <path
        class="jd-arrow jd-arrow--accent"
        :d="`M ${entry.centreX} ${BUS_Y + 2} L ${entry.centreX} ${METHOD_Y - 6}`"
        :marker-end="accentHead"
      />
      <rect
        class="jd-node__box"
        :class="{ 'jd-node__box--accent': index === 0 }"
        :x="entry.x"
        :y="METHOD_Y"
        :width="METHOD_W"
        :height="METHOD_H"
        rx="8"
      />
      <text class="jd-node__label" :x="entry.centreX" :y="METHOD_Y + METHOD_H / 2 - 8">
        {{ entry.label }}
      </text>
      <text v-if="entry.note" class="jd-node__sub" :x="entry.centreX" :y="METHOD_Y + METHOD_H / 2 + 14">
        {{ entry.note }}
      </text>
      <path
        class="jd-arrow jd-arrow--muted"
        :d="`M ${entry.centreX} ${METHOD_Y + METHOD_H + 4} L ${entry.centreX} ${CONVENTION_Y - 6}`"
      />
    </g>

    <!-- The shared reporting convention. -->
    <rect
      class="jd-node__box jd-node__box--accent"
      x="60"
      :y="CONVENTION_Y"
      width="1105"
      :height="CONVENTION_H"
      rx="8"
    />
    <text class="jd-node__label" x="612" :y="CONVENTION_Y + 22">{{ convention }}</text>
    <text
      v-if="conventionNote"
      class="jd-node__sub"
      x="612"
      :y="CONVENTION_Y + 42"
    >
      {{ conventionNote }}
    </text>
  </svg>
</template>
