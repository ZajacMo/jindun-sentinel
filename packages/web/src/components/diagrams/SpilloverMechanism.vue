<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The contagion mechanism.
 *
 * A shock hits one market.  The VAR turns it into a sequence of impulse
 * responses over the horizon H, and the generalised variance decomposition
 * turns those responses into the share of every *other* market's forecast
 * error variance that the shocked market is responsible for.  The loop back
 * to the left is what makes the contagion self-reinforcing.
 */
export interface SpilloverMarket {
  code: string
  label: string
}

const props = defineProps<{
  title: string
  /** The market the shock originates in. */
  shock: SpilloverMarket
  /** The remaining markets, in display order. */
  others: SpilloverMarket[]
  shockLabel: string
  responseLabel: string
  horizonLabel: string
  shareLabel: string
  varianceLabel: string
  feedbackLabel: string
  /** The number of steps the impulse responses are summed over. */
  horizon?: number
}>()

const uid = useDiagramId('spill')

const SHOCK_X = 30
const NODE_W = 150
const NODE_H = 44
const NODE_GAP = 18
const NODE_TOP = 96

const RESPONSE_X = 250
const RESPONSE_W = 320
const RESPONSE_TOP = 60
const RESPONSE_HEIGHT = 180

const SHARE_X = 620
const SHARE_W = 260

const VARIANCE_X = 920
const VARIANCE_W = 250

const horizon = computed(() => Math.max(props.horizon ?? 10, 2))

/** The markets that receive the shock, stacked on the left. */
const receiving = computed(() => props.others)

const nodeY = (index: number): number => NODE_TOP + index * (NODE_H + NODE_GAP)

/**
 * The impulse responses decay geometrically; the diagram shows their shape,
 * not measured values.
 */
const impulseBars = computed(() => {
  const bars: { x: number; height: number }[] = []
  const count = 8
  const slot = RESPONSE_W / count
  for (let index = 0; index < count; index += 1) {
    const decay = Math.exp(-index / 2.1)
    bars.push({
      x: RESPONSE_X + index * slot + slot * 0.18,
      height: Math.max(decay * RESPONSE_HEIGHT * 0.92, 3),
    })
  }
  return bars
})

const impulseAxisY = computed(() => RESPONSE_TOP + RESPONSE_HEIGHT)

/** The shares of the receiving markets, again as a shape rather than data. */
const shareBars = computed(() =>
  receiving.value.map((market, index) => ({
    market,
    width: 0.3 + 0.7 * (1 / (index + 1.6)),
    y: NODE_TOP + index * (NODE_H + NODE_GAP),
  })),
)

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const accentHead = computed(() => `url(#${uid}-accent)`)
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
      {{ shockLabel }} {{ shock.label }} — {{ responseLabel }} — {{ horizonLabel }} —
      {{ shareLabel }} — {{ varianceLabel }} — {{ feedbackLabel }}
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

    <text class="jd-diagram__title" x="30" y="26">{{ title }}</text>

    <!-- 1. The shock. -->
    <g>
      <rect
        class="jd-node__box jd-node__box--accent"
        :x="SHOCK_X"
        :y="NODE_TOP"
        :width="NODE_W"
        :height="NODE_H"
        rx="8"
      />
      <text class="jd-node__label" :x="SHOCK_X + NODE_W / 2" :y="NODE_TOP + NODE_H / 2 - 7">
        {{ shock.label }}
      </text>
      <text class="jd-node__sub" :x="SHOCK_X + NODE_W / 2" :y="NODE_TOP + NODE_H / 2 + 13">
        {{ shockLabel }}
      </text>
      <!-- The shock itself. -->
      <path
        :d="`M ${SHOCK_X + NODE_W / 2 - 9} 34 l 6 10 l -6 10 l 9 -10 z`"
        fill="var(--jd-diagram-reject)"
      />
      <text class="jd-diagram__small" :x="SHOCK_X + NODE_W / 2 + 16" y="48">
        {{ shockLabel }}
      </text>
    </g>

    <!-- 2. The impulse responses of the VAR. -->
    <g>
      <rect
        class="jd-node__box"
        :x="RESPONSE_X"
        :y="RESPONSE_TOP"
        :width="RESPONSE_W"
        :height="RESPONSE_HEIGHT"
        rx="8"
      />
      <text class="jd-diagram__label" :x="RESPONSE_X + RESPONSE_W / 2" :y="RESPONSE_TOP - 10">
        {{ responseLabel }}
      </text>
      <line
        class="jd-axis"
        :x1="RESPONSE_X + 16"
        :y1="impulseAxisY"
        :x2="RESPONSE_X + RESPONSE_W - 16"
        :y2="impulseAxisY"
      />
      <rect
        v-for="(bar, index) in impulseBars"
        :key="`impulse-${index}`"
        class="jd-bar"
        :x="bar.x"
        :y="impulseAxisY - bar.height"
        :width="RESPONSE_W / 8 - 8"
        :height="bar.height"
        rx="2"
      />
      <!-- The H-step horizon is marked below the axis. -->
      <path
        class="jd-flow"
        :d="`M ${RESPONSE_X + 16} ${impulseAxisY + 12} L ${RESPONSE_X + RESPONSE_W - 16} ${impulseAxisY + 12}`"
      />
      <path
        class="jd-flow"
        :d="`M ${RESPONSE_X + 16} ${impulseAxisY + 7} L ${RESPONSE_X + 16} ${impulseAxisY + 17}`"
      />
      <path
        class="jd-flow"
        :d="`M ${RESPONSE_X + RESPONSE_W - 16} ${impulseAxisY + 7} L ${RESPONSE_X + RESPONSE_W - 16} ${impulseAxisY + 17}`"
      />
      <text class="jd-diagram__small" :x="RESPONSE_X + RESPONSE_W / 2" :y="impulseAxisY + 30">
        {{ horizonLabel }} · H = {{ horizon }}
      </text>
    </g>

    <!-- 3. The share of every receiving market. -->
    <g>
      <text class="jd-diagram__label" :x="SHARE_X" :y="NODE_TOP - 18">{{ shareLabel }}</text>
      <g v-for="entry in shareBars" :key="`share-${entry.market.code}`">
        <text class="jd-diagram__small" :x="SHARE_X" :y="entry.y + 16">{{ entry.market.label }}</text>
        <rect
          class="jd-bar"
          :x="SHARE_X"
          :y="entry.y + 22"
          :width="SHARE_W * entry.width"
          height="12"
          rx="2"
        />
      </g>
    </g>

    <!-- 4. The forecast error variance that is explained. -->
    <g>
      <text class="jd-diagram__label" :x="VARIANCE_X" :y="NODE_TOP - 18">{{ varianceLabel }}</text>
      <g v-for="(market, index) in receiving" :key="`variance-${market.code}`">
        <rect
          class="jd-node__box"
          :x="VARIANCE_X"
          :y="nodeY(index)"
          :width="VARIANCE_W"
          :height="NODE_H"
          rx="8"
        />
        <text class="jd-node__label" :x="VARIANCE_X + VARIANCE_W / 2" :y="nodeY(index) + NODE_H / 2 - 7">
          {{ market.label }}
        </text>
        <text class="jd-node__sub" :x="VARIANCE_X + VARIANCE_W / 2" :y="nodeY(index) + NODE_H / 2 + 13">
          {{ shareLabel }}
        </text>
      </g>
    </g>

    <!-- The flow between the four stages. -->
    <path
      class="jd-arrow jd-arrow--accent"
      :d="`M ${SHOCK_X + NODE_W + 8} ${NODE_TOP + NODE_H / 2} L ${RESPONSE_X - 10} ${NODE_TOP + NODE_H / 2}`"
      :marker-end="accentHead"
    />
    <path
      class="jd-arrow jd-arrow--accent"
      :d="`M ${RESPONSE_X + RESPONSE_W + 8} ${NODE_TOP + NODE_H / 2} L ${SHARE_X - 10} ${NODE_TOP + NODE_H / 2}`"
      :marker-end="accentHead"
    />
    <path
      class="jd-arrow jd-arrow--accent"
      :d="`M ${SHARE_X + SHARE_W + 8} ${NODE_TOP + NODE_H / 2} L ${VARIANCE_X - 10} ${NODE_TOP + NODE_H / 2}`"
      :marker-end="accentHead"
    />

    <!-- The feedback loop: the receiving markets push back on the shock. -->
    <path
      class="jd-arrow jd-arrow--muted"
      :d="`M ${VARIANCE_X + VARIANCE_W / 2} ${nodeY(receiving.length - 1) + NODE_H + 14}
          L ${VARIANCE_X + VARIANCE_W / 2} 380
          L ${SHOCK_X + NODE_W / 2} 380
          L ${SHOCK_X + NODE_W / 2} ${NODE_TOP + NODE_H + 8}`"
      :marker-end="arrowHead"
    />
    <text class="jd-diagram__small" :x="(SHOCK_X + VARIANCE_X) / 2" y="374">
      {{ feedbackLabel }}
    </text>
  </svg>
</template>
