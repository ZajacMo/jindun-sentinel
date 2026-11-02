<script setup lang="ts">
import { computed } from 'vue'
import { useDiagramId } from '@/composables/useDiagramId'
import { useFormat } from '@/composables/useFormat'
import { useLabels } from '@/composables/useLabels'

/**
 * The spillover network, drawn as a chord diagram.
 *
 * Every node is a market (or a country).  The arc of a node is split into the
 * part of its own forecast error variance that other nodes explain and the
 * part that it explains in others; a ribbon connects the two, and its width is
 * the share of the variance that flows along it.
 *
 * The diagram is written by hand — no chart library is involved.
 */
const props = defineProps<{
  nodes: string[]
  matrix: number[][]
  title: string
}>()

const uid = useDiagramId('chord')

const format = useFormat()
const labels = useLabels()

const CENTRE_X = 320
const CENTRE_Y = 300
const RADIUS = 200
const THICKNESS = 14

interface Arc {
  code: string
  label: string
  start: number
  end: number
  labelX: number
  labelY: number
}

interface Ribbon {
  source: string
  target: string
  value: number
  d: string
}

function point(angle: number, radius = RADIUS): { x: number; y: number } {
  return {
    x: CENTRE_X + radius * Math.cos(angle),
    y: CENTRE_Y + radius * Math.sin(angle),
  }
}

const layout = computed(() => {
  const size = props.nodes.length
  const matrix = props.matrix
  if (size === 0) {
    return { arcs: [] as Arc[], ribbons: [] as Ribbon[] }
  }

  const cell = (row: number, column: number): number => {
    if (row === column) {
      return 0
    }
    const value = matrix[row]?.[column]
    return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0
  }

  // How much of a node's own variance comes from elsewhere, and how much of
  // the system it is responsible for.
  const outTotal = props.nodes.map((_node, row) =>
    props.nodes.reduce((sum, _column, column) => sum + cell(row, column), 0),
  )
  const inTotal = props.nodes.map((_node, column) =>
    props.nodes.reduce((sum, _other, row) => sum + cell(row, column), 0),
  )
  const total = props.nodes.map((_node, index) => (outTotal[index] as number) + (inTotal[index] as number))
  const grand = total.reduce((sum, value) => sum + value, 0)

  const arcs: Arc[] = []
  const ribbons: Ribbon[] = []
  if (grand <= 0) {
    return { arcs, ribbons }
  }

  const nodeStart: number[] = []
  const nodeEnd: number[] = []
  const outStart: number[] = []
  const inStart: number[] = []
  let cursor = -Math.PI / 2
  for (let index = 0; index < size; index += 1) {
    const span = ((total[index] as number) / grand) * Math.PI * 2
    const outSpan = span * ((outTotal[index] as number) / (total[index] as number))
    nodeStart.push(cursor)
    outStart.push(cursor)
    inStart.push(cursor + outSpan)
    nodeEnd.push(cursor + span)
    cursor += span
  }

  for (let index = 0; index < size; index += 1) {
    const mid = ((nodeStart[index] as number) + (nodeEnd[index] as number)) / 2
    const label = point(mid, RADIUS + 26)
    arcs.push({
      code: props.nodes[index] as string,
      label: labels.node(props.nodes[index] as string),
      start: nodeStart[index] as number,
      end: nodeEnd[index] as number,
      labelX: label.x,
      labelY: label.y,
    })
  }

  for (let row = 0; row < size; row += 1) {
    const rowTotal = outTotal[row] as number
    if (rowTotal <= 0) {
      continue
    }
    for (let column = 0; column < size; column += 1) {
      const value = cell(row, column)
      if (value <= 0) {
        continue
      }
      const columnTotal = inTotal[column] as number
      if (columnTotal <= 0) {
        continue
      }

      // The slice of the outgoing half of the row that belongs to this column.
      let prefixOut = 0
      for (let other = 0; other < column; other += 1) {
        prefixOut += cell(row, other)
      }
      const outSpan = (inStart[row] as number) - (outStart[row] as number)
      const a1 = (outStart[row] as number) + (prefixOut / rowTotal) * outSpan
      const a2 = (outStart[row] as number) + ((prefixOut + value) / rowTotal) * outSpan

      // The slice of the incoming half of the column that belongs to this row.
      let prefixIn = 0
      for (let other = 0; other < row; other += 1) {
        prefixIn += cell(other, column)
      }
      const inSpan = (nodeEnd[column] as number) - (inStart[column] as number)
      const b1 = (inStart[column] as number) + (prefixIn / columnTotal) * inSpan
      const b2 = (inStart[column] as number) + ((prefixIn + value) / columnTotal) * inSpan

      const p1 = point(a1)
      const p2 = point(a2)
      const p3 = point(b1)
      const p4 = point(b2)

      ribbons.push({
        source: props.nodes[row] as string,
        target: props.nodes[column] as string,
        value,
        d: [
          `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`,
          `A ${RADIUS} ${RADIUS} 0 ${a2 - a1 > Math.PI ? 1 : 0} 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`,
          `Q ${CENTRE_X} ${CENTRE_Y} ${p3.x.toFixed(2)} ${p3.y.toFixed(2)}`,
          `A ${RADIUS} ${RADIUS} 0 ${b2 - b1 > Math.PI ? 1 : 0} 1 ${p4.x.toFixed(2)} ${p4.y.toFixed(2)}`,
          `Q ${CENTRE_X} ${CENTRE_Y} ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`,
          'Z',
        ].join(' '),
      })
    }
  }

  return { arcs, ribbons }
})

const palette = ['#0f766e', '#b3261e', '#9a5b00', '#3d5878', '#7a4f9c', '#1f6f43']

function colourFor(index: number): string {
  return palette[index % palette.length] as string
}

function arcPath(arc: Arc): string {
  const inner = RADIUS - THICKNESS
  const outer = point(arc.start, RADIUS)
  const innerEnd = point(arc.end, inner)
  const outerEnd = point(arc.end, RADIUS)
  const innerStart = point(arc.start, inner)
  const large = arc.end - arc.start > Math.PI ? 1 : 0
  return [
    `M ${outer.x.toFixed(2)} ${outer.y.toFixed(2)}`,
    `A ${RADIUS} ${RADIUS} 0 ${large} 1 ${outerEnd.x.toFixed(2)} ${outerEnd.y.toFixed(2)}`,
    `L ${innerEnd.x.toFixed(2)} ${innerEnd.y.toFixed(2)}`,
    `A ${inner} ${inner} 0 ${large} 0 ${innerStart.x.toFixed(2)} ${innerStart.y.toFixed(2)}`,
    'Z',
  ].join(' ')
}
</script>

<template>
  <svg
    class="jd-diagram"
    viewBox="0 0 640 600"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-labelledby="`${uid}-title ${uid}-desc`"
  >
    <title :id="`${uid}-title`">{{ title }}</title>
    <desc :id="`${uid}-desc`">{{ layout.arcs.map((arc) => arc.label).join(', ') }}</desc>

    <text class="jd-diagram__title" x="20" y="24">{{ title }}</text>

    <!-- The ribbons. -->
    <g>
      <path
        v-for="(ribbon, index) in layout.ribbons"
        :key="`ribbon-${index}`"
        :d="ribbon.d"
        :fill="colourFor(index)"
        fill-opacity="0.32"
        stroke="none"
      >
        <title>{{ ribbon.source }} → {{ ribbon.target }}: {{ format.share(ribbon.value, 2) }}</title>
      </path>
    </g>

    <!-- The nodes. -->
    <g>
      <path
        v-for="(arc, index) in layout.arcs"
        :key="`arc-${arc.code}`"
        :d="arcPath(arc)"
        :fill="colourFor(index)"
        stroke="var(--jd-surface)"
        stroke-width="1"
      />
      <text
        v-for="(arc, index) in layout.arcs"
        :key="`label-${arc.code}`"
        class="jd-diagram__label"
        :x="arc.labelX"
        :y="arc.labelY"
        text-anchor="middle"
        :fill="colourFor(index)"
      >
        {{ arc.label }}
      </text>
    </g>
  </svg>
</template>
