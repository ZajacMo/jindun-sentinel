import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PipelineDiagram from '@/components/diagrams/PipelineDiagram.vue'
import SpilloverMechanism from '@/components/diagrams/SpilloverMechanism.vue'
import RegimeMechanism from '@/components/diagrams/RegimeMechanism.vue'
import AlertLoop from '@/components/diagrams/AlertLoop.vue'
import GlobalNetwork from '@/components/diagrams/GlobalNetwork.vue'
import MarketIndexMechanism from '@/components/diagrams/MarketIndexMechanism.vue'
import QualityGateMechanism from '@/components/diagrams/QualityGateMechanism.vue'
import EstimatorStack from '@/components/diagrams/EstimatorStack.vue'

/**
 * The mechanism diagrams are hand-written SVG.  They have to be present on
 * the page, they have to carry an accessible name, and they must not depend
 * on a chart library to be rendered.
 */
const STAGES = [
  { label: 'Source' },
  { label: 'Adapters' },
  { label: 'Data Quality' },
  { label: 'Percentile' },
  { label: 'PCA' },
  { label: 'Composite' },
  { label: 'Probability' },
  { label: 'Alerts' },
  { label: 'API' },
  { label: 'UI' },
]

const MARKETS = [
  { code: 'equity', label: 'Equity' },
  { code: 'bond', label: 'Bond' },
  { code: 'fx', label: 'Foreign Exchange' },
  { code: 'money', label: 'Money Market' },
  { code: 'derivative', label: 'Derivatives' },
]

const diagramCases = [
  {
    name: 'PipelineDiagram',
    component: PipelineDiagram,
    props: { title: 'Pipeline', stages: STAGES, rejection: 'Failure' },
  },
  {
    name: 'SpilloverMechanism',
    component: SpilloverMechanism,
    props: {
      title: 'Spillover',
      shock: MARKETS[0],
      others: MARKETS.slice(1),
      shockLabel: 'Source',
      responseLabel: 'Paper Equations',
      horizonLabel: 'Daily',
      shareLabel: 'Own Risk Share',
      varianceLabel: 'Spill-In',
      feedbackLabel: 'Spillover',
      horizon: 10,
    },
  },
  {
    name: 'RegimeMechanism',
    component: RegimeMechanism,
    props: {
      title: 'Regime',
      moderateLabel: 'Moderate',
      highLabel: 'High',
      axisLabel: 'Composite',
      mixtureLabel: 'Percentile',
      chainLabel: 'Moderate / High',
      moderateMean: 0,
      moderateStd: 0.2,
      highMean: 0.6,
      highStd: 0.3,
      highWeight: 0.4,
      stepLabels: ['Composite', 'Deviation', 'Percentile', 'Probability'],
      resultLabels: ['Moderate', 'High'],
    },
  },
  {
    name: 'AlertLoop',
    component: AlertLoop,
    props: {
      title: 'Alerts',
      detect: 'Spillover',
      attribute: 'Sector',
      notify: 'Alerts',
      acknowledge: 'Close',
      resolve: 'OK',
      silence: 'Daily',
      loopLabel: 'Retry',
    },
  },
  {
    name: 'GlobalNetwork',
    component: GlobalNetwork,
    props: {
      title: 'Global',
      countries: [
        { code: 'CN', label: 'China' },
        { code: 'US', label: 'United States' },
        { code: 'EU', label: 'Euro Area' },
        { code: 'GB', label: 'United Kingdom' },
        { code: 'JP', label: 'Japan' },
      ],
      layers: MARKETS.map((market) => market.label),
      anchorCountry: 'EU',
      anchorLabel: 'ECB CISS',
      bisLabel: 'BIS',
      layersLabel: 'Sector',
    },
  },
  {
    name: 'MarketIndexMechanism',
    component: MarketIndexMechanism,
    props: {
      title: 'Composite',
      stages: STAGES.slice(0, 6),
      composite: 'Composite',
    },
  },
  {
    name: 'QualityGateMechanism',
    component: QualityGateMechanism,
    props: {
      title: 'Data Quality',
      source: 'Source',
      checks: ['has_observations', 'freshness', 'completeness'],
      verdict: 'Data Quality',
      publish: 'OK',
      block: 'Failure',
    },
  },
  {
    name: 'EstimatorStack',
    component: EstimatorStack,
    props: {
      title: 'Methodology',
      model: 'VAR',
      vma: 'VMA',
      decomposition: 'Paper Equations',
      estimators: [
        { code: 'paper_equation', label: 'Paper Equations' },
        { code: 'sims_structural', label: 'Sims FEVD' },
      ],
      convention: 'Own Risk Share',
      conventionNote: 'Notes',
    },
  },
] as const

describe('mechanism diagrams', () => {
  it.each(diagramCases)('$name renders an accessible inline SVG', (entry) => {
    const wrapper = mount(entry.component, { props: entry.props as never })

    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    expect(svg.attributes('role')).toBe('img')
    expect(svg.attributes('viewBox')).toBeTruthy()
    expect(svg.attributes('preserveAspectRatio')).toBeTruthy()

    const title = wrapper.find('title')
    expect(title.exists()).toBe(true)
    expect(title.text().length).toBeGreaterThan(0)

    const description = wrapper.find('desc')
    expect(description.exists()).toBe(true)
    expect(description.text().length).toBeGreaterThan(0)

    // The diagram is drawn, not an empty canvas.
    expect(wrapper.findAll('rect').length + wrapper.findAll('path').length).toBeGreaterThan(1)

    wrapper.unmount()
  })
})

describe('PipelineDiagram', () => {
  it('draws every stage and the rejection branch', () => {
    const wrapper = mount(PipelineDiagram, {
      props: { title: 'Pipeline', stages: STAGES, rejection: 'Failure' },
    })

    // Ten stages plus the rejection node.
    expect(wrapper.findAll('.jd-node__box').length).toBeGreaterThanOrEqual(11)
    expect(wrapper.findAll('.jd-node__box--reject').length).toBe(1)
    expect(wrapper.findAll('path.jd-arrow').length).toBeGreaterThanOrEqual(10)

    const texts = wrapper.findAll('text').map((node) => node.text())
    for (const stage of STAGES) {
      expect(texts).toContain(stage.label)
    }
    expect(texts).toContain('Failure')

    wrapper.unmount()
  })
})
