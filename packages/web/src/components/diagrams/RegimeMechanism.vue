<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The regime identification and the risk probability model.
 *
 * The logarithm of the composite index is modelled as a mixture of two normal
 * components — a moderate and a high stress state.  The Markov model supplies
 * the two means and variances; the mixture turns them into the probability
 * that the economy currently sits in the high stress state, which is what the
 * alerting rules are evaluated against.
 */
const props = defineProps<{
  title: string
  moderateLabel: string
  highLabel: string
  axisLabel: string
  mixtureLabel: string
  chainLabel: string
  moderateMean: number
  moderateStd: number
  highMean: number
  highStd: number
  /** The weight of the high stress component. */
  highWeight: number
  /** The four steps of the probability computation. */
  stepLabels: string[]
  /** The two resulting probabilities. */
  resultLabels: string[]
}>()

const uid = useDiagramId('regime')

const CHART_X = 60
const CHART_W = 600
const BASELINE_Y = 250
const CHART_TOP = 60

const X_MIN = -3
const X_MAX = 4

function density(value: number, mean: number, std: number): number {
  const safeStd = Math.max(std, 1e-6)
  const z = (value - mean) / safeStd
  return (Math.exp(-0.5 * z * z) / (safeStd * Math.sqrt(2 * Math.PI)))
}

function curvePath(mean: number, std: number, weight: number): string {
  const parts: string[] = []
  const steps = 140
  const peak = Math.max(
    density(props.moderateMean, props.moderateMean, props.moderateStd),
    density(props.highMean, props.highMean, props.highStd),
    1e-6,
  )
  for (let index = 0; index <= steps; index += 1) {
    const ratio = index / steps
    const value = X_MIN + ratio * (X_MAX - X_MIN)
    const x = CHART_X + ratio * CHART_W
    const y = BASELINE_Y - (density(value, mean, std) / peak) * weight * (BASELINE_Y - CHART_TOP)
    parts.push(`${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`)
  }
  return parts.join(' ')
}

const moderatePath = computed(() =>
  curvePath(props.moderateMean, props.moderateStd, 1),
)
const highPath = computed(() => curvePath(props.highMean, props.highStd, 1))
const mixturePath = computed(() => {
  const parts: string[] = []
  const steps = 140
  const peak = Math.max(
    density(props.moderateMean, props.moderateMean, props.moderateStd),
    density(props.highMean, props.highMean, props.highStd),
    1e-6,
  )
  for (let index = 0; index <= steps; index += 1) {
    const ratio = index / steps
    const value = X_MIN + ratio * (X_MAX - X_MIN)
    const x = CHART_X + ratio * CHART_W
    const mix =
      (1 - props.highWeight) * density(value, props.moderateMean, props.moderateStd) +
      props.highWeight * density(value, props.highMean, props.highStd)
    const y = BASELINE_Y - (mix / peak) * (BASELINE_Y - CHART_TOP)
    parts.push(`${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`)
  }
  return parts.join(' ')
})

const moderateMeanX = computed(
  () => CHART_X + ((props.moderateMean - X_MIN) / (X_MAX - X_MIN)) * CHART_W,
)
const highMeanX = computed(
  () => CHART_X + ((props.highMean - X_MIN) / (X_MAX - X_MIN)) * CHART_W,
)

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const accentHead = computed(() => `url(#${uid}-accent)`)
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 1200 470"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">
      {{ mixtureLabel }}: {{ moderateLabel }} {{ highLabel }}. {{ chainLabel }}.
      {{ stepLabels.join(' → ') }}. {{ resultLabels.join(', ') }}.
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

    <!-- The two-component mixture over the log composite. -->
    <g>
      <text class="jd-diagram__label" :x="CHART_X" :y="CHART_TOP - 16">{{ mixtureLabel }}</text>
      <line
        class="jd-axis"
        :x1="CHART_X"
        :y1="BASELINE_Y"
        :x2="CHART_X + CHART_W"
        :y2="BASELINE_Y"
      />
      <path class="jd-curve jd-curve--moderate" :d="moderatePath" />
      <path class="jd-curve jd-curve--high" :d="highPath" />
      <path
        :d="`${mixturePath} L ${CHART_X + CHART_W} ${BASELINE_Y} L ${CHART_X} ${BASELINE_Y} Z`"
        fill="var(--jd-diagram-accent-soft)"
        stroke="none"
      />
      <path class="jd-flow" :d="mixturePath" />
      <line
        class="jd-gridline"
        :x1="moderateMeanX"
        :y1="BASELINE_Y"
        :x2="moderateMeanX"
        :y2="BASELINE_Y - 26"
        stroke-dasharray="3 3"
      />
      <line
        class="jd-gridline"
        :x1="highMeanX"
        :y1="BASELINE_Y"
        :x2="highMeanX"
        :y2="BASELINE_Y - 26"
        stroke-dasharray="3 3"
      />
      <text class="jd-diagram__small" :x="moderateMeanX" :y="BASELINE_Y + 16" text-anchor="middle">
        {{ moderateLabel }}
      </text>
      <text class="jd-diagram__small" :x="highMeanX" :y="BASELINE_Y + 16" text-anchor="middle">
        {{ highLabel }}
      </text>
      <text class="jd-diagram__small" :x="CHART_X + CHART_W / 2" :y="BASELINE_Y + 34" text-anchor="middle">
        {{ axisLabel }}
      </text>
    </g>

    <!-- The two-state Markov chain. -->
    <g>
      <text class="jd-diagram__label" x="760" y="52">{{ chainLabel }}</text>
      <rect class="jd-node__box" x="820" y="80" width="200" height="56" rx="8" />
      <text class="jd-node__label" x="920" y="101">{{ moderateLabel }}</text>
      <text class="jd-node__sub" x="920" y="120">p₁₁</text>

      <rect class="jd-node__box jd-node__box--accent" x="820" y="180" width="200" height="56" rx="8" />
      <text class="jd-node__label" x="920" y="201">{{ highLabel }}</text>
      <text class="jd-node__sub" x="920" y="220">p₂₂</text>

      <path class="jd-arrow" d="M 870 80 Q 920 26 970 80" :marker-end="arrowHead" />
      <path class="jd-arrow" d="M 870 180 Q 920 126 970 180" :marker-end="arrowHead" />
      <path class="jd-arrow jd-arrow--accent" d="M 1030 108 C 1096 108 1096 208 1030 208" :marker-end="accentHead" />
      <text class="jd-diagram__small" x="1064" y="152" text-anchor="middle">p₁₂</text>
      <path class="jd-arrow" d="M 810 208 C 744 208 744 108 810 108" :marker-end="arrowHead" />
      <text class="jd-diagram__small" x="764" y="152" text-anchor="middle">p₂₁</text>
    </g>

    <!-- The probability computation. -->
    <g>
      <text class="jd-diagram__label" x="60" y="292">{{ resultLabels.join(' · ') }}</text>
      <g v-for="(label, index) in stepLabels" :key="`step-${index}`">
        <rect
          class="jd-node__box"
          :x="60 + index * 190"
          y="312"
          width="160"
          height="56"
          rx="8"
        />
        <text
          class="jd-node__label"
          :x="140 + index * 190"
          y="340"
        >
          {{ label }}
        </text>
        <path
          v-if="index < stepLabels.length - 1"
          class="jd-arrow"
          :d="`M ${228 + index * 190} 340 L ${242 + index * 190} 340`"
          :marker-end="arrowHead"
        />
      </g>
      <path class="jd-arrow jd-arrow--accent" d="M 800 340 L 840 340" :marker-end="accentHead" />
      <rect class="jd-node__box jd-node__box--accent" x="850" y="300" width="150" height="40" rx="8" />
      <text class="jd-node__label" x="925" y="325">{{ resultLabels[0] }}</text>
      <rect class="jd-node__box" x="850" y="350" width="150" height="40" rx="8" />
      <text class="jd-node__label" x="925" y="375">{{ resultLabels[1] }}</text>
    </g>
  </svg>
</template>
