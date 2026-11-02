<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'

/**
 * The alerting loop.
 *
 * A rule fires, the alert is attributed to the market that caused it, the
 * notification goes out, an analyst acknowledges it and the alert is finally
 * resolved.  The silence window sits between the notification and the
 * acknowledgement: while it is open, the same rule does not fire again.
 */
const props = defineProps<{
  title: string
  detect: string
  attribute: string
  notify: string
  acknowledge: string
  resolve: string
  silence: string
  silenceDetail?: string
  loopLabel: string
}>()

const uid = useDiagramId('alert')

const CENTRE_X = 600
const CENTRE_Y = 230
const RADIUS = 150
const NODE_W = 160
const NODE_H = 54

interface Node {
  key: string
  label: string
  x: number
  y: number
}

const nodes = computed<Node[]>(() => {
  const angles = [-90, -18, 54, 126, 198]
  const labels = [
    props.detect,
    props.attribute,
    props.notify,
    props.acknowledge,
    props.resolve,
  ]
  return angles.map((angle, index) => {
    const radians = (angle * Math.PI) / 180
    return {
      key: `node-${index}`,
      label: labels[index] as string,
      x: CENTRE_X + RADIUS * Math.cos(radians),
      y: CENTRE_Y + RADIUS * Math.sin(radians),
    }
  })
})

/** Straight arrows between the node boxes, clipped at their edges. */
const links = computed(() => {
  const result: { from: Node; to: Node; d: string }[] = []
  const list = nodes.value
  for (let index = 0; index < list.length - 1; index += 1) {
    const from = list[index] as Node
    const to = list[index + 1] as Node
    const dx = to.x - from.x
    const dy = to.y - from.y
    const length = Math.hypot(dx, dy) || 1
    const ux = dx / length
    const uy = dy / length
    const offset = (): number =>
      Math.min(NODE_W / 2 / Math.max(Math.abs(ux), 1e-6), NODE_H / 2 / Math.max(Math.abs(uy), 1e-6))
    const startX = from.x + ux * offset()
    const startY = from.y + uy * offset()
    const endX = to.x - ux * offset()
    const endY = to.y - uy * offset()
    result.push({ from, to, d: `M ${startX.toFixed(2)} ${startY.toFixed(2)} L ${endX.toFixed(2)} ${endY.toFixed(2)}` })
  }
  return result
})

/** The feedback arc that closes the loop from the resolution back to the detection. */
const feedback = computed(() => {
  const detect = nodes.value[0] as Node
  const resolve = nodes.value[4] as Node
  const startX = resolve.x - NODE_W / 2
  const startY = resolve.y
  const endX = detect.x - NODE_W / 2
  const endY = detect.y
  return {
    d: `M ${startX} ${startY} C ${startX - 150} ${startY - 30}, ${endX - 150} ${endY + 30}, ${endX} ${endY}`,
    labelX: (startX + endX) / 2 - 110,
    labelY: (startY + endY) / 2,
  }
})

/** The silence window sits on the link between the notification and the acknowledgement. */
const silenceGate = computed(() => {
  const link = links.value[2]
  if (!link) {
    return null
  }
  const midpointX = (link.from.x + link.to.x) / 2
  const midpointY = (link.from.y + link.to.y) / 2
  return {
    x: midpointX - 90,
    y: midpointY + 18,
    width: 180,
    height: 44,
    labelX: midpointX,
    labelY: midpointY + 40,
    detailX: midpointX,
    detailY: midpointY + 58,
  }
})

const arrowHead = computed(() => `url(#${uid}-arrow)`)
const accentHead = computed(() => `url(#${uid}-accent)`)
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
      {{ detect }} → {{ attribute }} → {{ notify }} → {{ acknowledge }} → {{ resolve }} →
      {{ detect }}. {{ silence }}.
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

    <!-- The ring of the loop. -->
    <circle
      class="jd-ring"
      :cx="CENTRE_X"
      :cy="CENTRE_Y"
      :r="RADIUS"
      fill="none"
    />

    <path
      v-for="(link, index) in links"
      :key="`link-${index}`"
      class="jd-arrow"
      :class="{ 'jd-arrow--muted': index === 2 }"
      :d="link.d"
      :marker-end="arrowHead"
    />

    <!-- The silence window on the notification link. -->
    <g v-if="silenceGate">
      <rect
        class="jd-node__box jd-node__box--reject"
        :x="silenceGate.x"
        :y="silenceGate.y"
        :width="silenceGate.width"
        :height="silenceGate.height"
        rx="8"
      />
      <text class="jd-node__label" :x="silenceGate.labelX" :y="silenceGate.y + 18">
        {{ silence }}
      </text>
      <text v-if="silenceDetail" class="jd-node__sub" :x="silenceGate.detailX" :y="silenceGate.detailY">
        {{ silenceDetail }}
      </text>
    </g>

    <!-- The five steps. -->
    <g v-for="(node, index) in nodes" :key="node.key">
      <rect
        class="jd-node__box"
        :class="{ 'jd-node__box--accent': index === 0 }"
        :x="node.x - NODE_W / 2"
        :y="node.y - NODE_H / 2"
        :width="NODE_W"
        :height="NODE_H"
        rx="8"
      />
      <text class="jd-node__label" :x="node.x" :y="node.y + 5">{{ node.label }}</text>
    </g>

    <!-- The loop closes. -->
    <path class="jd-arrow jd-arrow--accent" :d="feedback.d" :marker-end="accentHead" />
    <text class="jd-diagram__small" :x="feedback.labelX" :y="feedback.labelY">
      {{ loopLabel }}
    </text>
  </svg>
</template>
