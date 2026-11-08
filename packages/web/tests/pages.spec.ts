import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import { i18n, setActiveLocale } from '@/i18n'
import { routes } from '@/router'

/**
 * The API is mocked at the HTTP layer, so the real normalisers of
 * `src/api/types.ts` still run and the pages see the shapes they get in
 * production.
 */
const fixtures = vi.hoisted(() => ({
  countries: [
    {
      code: 'CN',
      name_en: 'China',
      name_local: '中国',
      currency: 'CNY',
      timezone: 'Asia/Shanghai',
      locale: 'zh-CN',
      enabled: true,
      as_of: '2024-10-18',
      ciss_area: null,
    },
  ],
  index: {
    country_code: 'CN',
    as_of: '2024-10-18',
    composite: [
      { date: '2024-10-16', value: 0.61 },
      { date: '2024-10-17', value: 0.64 },
      { date: '2024-10-18', value: 0.72 },
    ],
    percentile: [
      { date: '2024-10-16', value: 0.61 },
      { date: '2024-10-17', value: 0.64 },
      { date: '2024-10-18', value: 0.72 },
    ],
    deviation: [
      { date: '2024-10-16', value: 0.01 },
      { date: '2024-10-17', value: 0.03 },
      { date: '2024-10-18', value: 0.06 },
    ],
    market_indices: {
      dates: ['2024-10-16', '2024-10-17', '2024-10-18'],
      series: {
        equity: [0.5, 0.52, 0.58],
        bond: [0.4, 0.42, 0.47],
        fx: [0.3, 0.33, 0.36],
        money: [0.2, 0.21, 0.25],
        derivative: [0.6, 0.63, 0.69],
      },
    },
    regime: {
      dates: ['2024-10-16', '2024-10-17', '2024-10-18'],
      labels: ['moderate', 'moderate', 'high'],
      probability_moderate: [0.8, 0.7, 0.3],
      probability_high: [0.2, 0.3, 0.7],
      params: {
        moderate_mean: 0,
        moderate_std: 0.2,
        high_mean: 0.6,
        high_std: 0.3,
      },
    },
    warnings: [],
  },
  spillover: {
    scope: 'CN',
    nodes: ['equity', 'bond', 'fx', 'money', 'derivative'],
    matrix: [
      [0.9, 0.03, 0.02, 0.02, 0.03],
      [0.08, 0.86, 0.02, 0.02, 0.02],
      [0.05, 0.04, 0.85, 0.03, 0.03],
      [0.01, 0.04, 0.02, 0.91, 0.02],
      [0.4, 0.01, 0.01, 0.04, 0.54],
    ],
    total_spillout: {
      equity: 0.54,
      bond: 0.12,
      fx: 0.07,
      money: 0.11,
      derivative: 0.1,
    },
    total_spillin: {
      equity: 0.1,
      bond: 0.12,
      fx: 0.07,
      money: 0.11,
      derivative: 0.6,
    },
    net: {
      equity: 0.44,
      bond: 0,
      fx: 0,
      money: 0,
      derivative: -0.5,
    },
    horizon: 10,
    method: 'paper_equation',
    window: null,
    notes: [
      {
        key: 'spillover.note.method',
        params: {
          method: 'paper_equation',
          order: 5,
          criterion: 'bic',
          horizon: 10,
          start: '2011-11-07',
          end: '2024-10-18',
        },
      },
    ],
    var_order: 5,
  },
  cycle: {
    status: 'estimated',
    source: 'BIS',
    frequency: 'Q',
    orientation: {
      anchor: 'credit_gap_mean',
      correlation: 0.8412,
      gap_direction: 'wider',
      growth_direction: 'slower',
    },
    dates: ['2020-01-01', '2020-04-01', '2020-07-01'],
    factor: [0.1, -0.2, 0.35],
    loadings: { credit_gap_cn: 0.42, global_credit_yoy: -0.31 },
    explained_variance_ratio: [0.349, 0.21],
    cumulative_variance_ratio: [0.349, 0.559],
    factor_standard_deviation: 1.0,
    observations: 3,
    inputs: [],
    cross_check: {
      available: true,
      correlation: 0.42,
      observations: 3,
    },
    notes: [],
  },
  alerts: [
    {
      alert_id: 'CN.composite.p1.2024-10-18',
      country_code: 'CN',
      rule_id: 'composite.p1',
      severity: 'P1',
      state: 'active',
      fired_at: '2024-10-18T08:00:00Z',
      message_key: 'alert.composite_p1',
      message_params: { country: 'CN', value: 0.92, threshold: 0.9 },
      attribution: {},
      detail: {},
    },
  ],
  quality: {
    generated_at: '2024-10-18T08:00:00Z',
    passed: true,
    counts: { total: 1, ok: 1, warning: 0, failure: 0 },
    series: [
      {
        series_id: 'equity.pe_ratio',
        adapter: 'akshare',
        country_code: 'CN',
        severity: 'ok',
        passed: true,
        observations: 1200,
        first_date: '2020-01-01',
        last_date: '2024-10-18',
        checks: [
          {
            name: 'freshness',
            passed: true,
            severity: 'ok',
            measured: 0,
            threshold: 5,
            message: '',
          },
        ],
      },
    ],
  },
}))

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client')
  const get = vi.fn(async (path: string) => {
    if (path === '/api/v1/countries') {
      return fixtures.countries
    }
    if (path.includes('/index')) {
      return fixtures.index
    }
    if (path.includes('/spillover')) {
      return fixtures.spillover
    }
    if (path.includes('/cycle')) {
      return fixtures.cycle
    }
    if (path.includes('/alerts')) {
      return fixtures.alerts
    }
    if (path.includes('/data-quality')) {
      return fixtures.quality
    }
    if (path.includes('/gsib')) {
      return []
    }
    if (path.includes('/health')) {
      return { status: 'ok' }
    }
    return {}
  })
  return {
    ...actual,
    apiClient: {
      baseUrl: 'http://localhost:8000',
      url: (path: string) => path,
      get,
    },
  }
})

const PAGES = [
  { name: 'overview', route: 'overview', path: '/' },
  { name: 'countries', route: 'countries', path: '/countries' },
  { name: 'country-detail', route: 'country-detail', path: '/countries/CN' },
  { name: 'spillover', route: 'spillover', path: '/spillover' },
  { name: 'alerts', route: 'alerts', path: '/alerts' },
  { name: 'data-quality', route: 'data-quality', path: '/data-quality' },
  { name: 'methodology', route: 'methodology', path: '/methodology' },
]

/**
 * Mounting a workspace page builds its whole layout, and the overview page
 * draws four ECharts instances inside jsdom, which has no canvas.  The
 * overview case needs roughly three seconds on a developer machine, so the
 * default five-second timeout leaves almost no margin: a shared CI runner is
 * easily twice as slow, and the suite then fails on a timeout rather than on
 * a defect.  The timeout below is generous enough for that, and only these
 * page-rendering cases carry it — the rest of the suite runs in milliseconds.
 */
const PAGE_TIMEOUT = 20000

async function renderPage(routeName: string, path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()

  const component = routes.find((route) => route.name === routeName)?.component
  if (typeof component !== 'function') {
    throw new Error(`no component for ${path}`)
  }
  const module = (await (component as () => Promise<{ default: unknown }>)()) as {
    default: unknown
  }
  const wrapper = mount(module.default as never, {
    global: { plugins: [router, i18n, ElementPlus] },
  })
  await flushPromises()
  return wrapper
}

describe('workspace pages', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it.each(PAGES)('$name renders and carries a mechanism diagram', async (page) => {
    const wrapper = await renderPage(page.route, page.path)

    expect(wrapper.find('h1').exists()).toBe(true)
    const svgs = wrapper.findAll('svg')
    expect(svgs.length).toBeGreaterThanOrEqual(1)
    expect(svgs.some((svg) => svg.attributes('role') === 'img')).toBe(true)

    wrapper.unmount()
  }, PAGE_TIMEOUT)

  it('uses the mechanism diagrams of the brief', async () => {
    const titles = new Set<string>()

    for (const page of PAGES) {
      const wrapper = await renderPage(page.route, page.path)
      for (const svg of wrapper.findAll('svg')) {
        const title = svg.find('title')
        if (title.exists()) {
          titles.add(title.text())
        }
      }
      wrapper.unmount()
    }

    // The five diagrams the brief requires, plus the three additional ones.
    expect(titles.size).toBeGreaterThanOrEqual(5)
  }, PAGE_TIMEOUT)

  it('shows the localised labels of the active locale', async () => {
    const wrapper = await renderPage('overview', '/')
    const heading = wrapper.find('h1').text()
    expect(heading).not.toBe('nav.overview')
    expect(heading.length).toBeGreaterThan(0)
    wrapper.unmount()
  }, PAGE_TIMEOUT)

  it('renders the spillover matrix of the selected country', async () => {
    const wrapper = await renderPage('spillover', '/spillover')
    const text = wrapper.text()
    expect(text).toContain('equity')
    wrapper.unmount()
  }, PAGE_TIMEOUT)

  /**
   * The quality table bound its `Source` column to the snake_case key of the API
   * payload, while the API client normalises every field to camelCase before the
   * table sees it.  The column was therefore empty on every row and the reader
   * could not tell which series the verdict belonged to.
   */
  it('shows the identifier of every fetched series in the quality table', async () => {
    const wrapper = await renderPage('data-quality', '/data-quality')
    expect(wrapper.text()).toContain('equity.pe_ratio')
    wrapper.unmount()
  }, PAGE_TIMEOUT)

  /**
   * The artefact carries a catalogue key and the facts that fill it, never a
   * finished sentence.  This is the regression test for the defect where the
   * server's English prose reached the screen in every locale: a note must be
   * rendered from the catalogue in the reader's language, and the key must
   * never be what the reader sees.
   */
  it('renders the notes of the artefact in the active locale', async () => {
    setActiveLocale('en-US')
    const english = await renderPage('spillover', '/spillover')
    expect(english.text()).toContain('horizon 10')
    expect(english.text()).not.toContain('spillover.note.method')
    english.unmount()

    setActiveLocale('zh-CN')
    const chinese = await renderPage('spillover', '/spillover')
    expect(chinese.text()).toContain('预测期 10')
    expect(chinese.text()).not.toContain('spillover.note.method')
    chinese.unmount()

    setActiveLocale('en-US')
  }, PAGE_TIMEOUT)

  /**
   * The orientation of the factor used to be one English sentence written by
   * the pipeline.  It is now the facts — the anchor, the correlation and the
   * direction of each driver — and the catalogue turns them into a sentence in
   * the reader's language.
   */
  it('renders the orientation of the cycle factor in the active locale', async () => {
    setActiveLocale('en-US')
    const english = await renderPage('spillover', '/spillover')
    expect(english.text()).toContain('the mean of the standardised credit gaps')
    expect(english.text()).toContain('a wider credit-to-GDP gap and slower global credit growth')
    english.unmount()

    setActiveLocale('zh-CN')
    const chinese = await renderPage('spillover', '/spillover')
    expect(chinese.text()).toContain('标准化后的信用缺口均值')
    expect(chinese.text()).toContain('信用缺口更宽、全球信贷增速更慢')
    chinese.unmount()

    setActiveLocale('en-US')
  }, PAGE_TIMEOUT)
})
