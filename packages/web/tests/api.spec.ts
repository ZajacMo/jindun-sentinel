import { describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError } from '@/api/client'
import {
  normaliseAlerts,
  normaliseCountries,
  normaliseGsib,
  normaliseIndexPayload,
  normaliseQualityPayload,
  normaliseSpilloverPayload,
} from '@/api/types'

/**
 * The payload shapes below are the ones the API actually serves; the
 * normalisers have to turn them into the internal shapes without losing
 * anything.
 */
describe('payload normalisers', () => {
  it('normalises the index response of a country', () => {
    const payload = normaliseIndexPayload(
      {
        country_code: 'CN',
        as_of: '2024-10-18',
        lens: 'percentile',
        composite: [{ date: '2024-10-18', value: 0.72 }],
        percentile: [{ date: '2024-10-18', value: 0.72 }],
        deviation: [{ date: '2024-10-18', value: 0.06 }],
        market_indices: {
          equity: [{ date: '2024-10-18', value: 0.58 }],
          bond: [{ date: '2024-10-18', value: 0.47 }],
        },
        market_dates: ['2024-10-18'],
        regime: {
          dates: ['2024-10-18'],
          labels: ['high'],
          probability_moderate: [0.3],
          probability_high: [0.7],
          params: { moderate_mean: 0, high_mean: 0.6 },
        },
        warnings: [],
      },
      'CN',
    )

    expect(payload.countryCode).toBe('CN')
    expect(payload.asOf).toBe('2024-10-18')
    expect(payload.composite).toHaveLength(1)
    expect(payload.marketIndices.map((market) => market.code)).toEqual(['equity', 'bond'])
    expect(payload.marketIndices[0]?.points[0]).toEqual({ date: '2024-10-18', value: 0.58 })
    expect(payload.regime.points[0]?.regime).toBe('high')
    expect(payload.regime.points[0]?.probabilityHigh).toBe(0.7)
    expect(payload.regime.params.high_mean).toBe(0.6)
  })

  it('normalises the country list', () => {
    const countries = normaliseCountries({
      countries: [
        {
          code: 'CN',
          name_en: 'CN',
          as_of: '2024-10-18',
          markets: ['equity', 'bond'],
          latest_percentile: 0.72,
          latest_deviation: 0.06,
          regime: 'high',
          probability_high: 0.7,
          open_alerts: 1,
        },
      ],
    })

    expect(countries).toHaveLength(1)
    expect(countries[0]?.code).toBe('CN')
    expect(countries[0]?.markets).toEqual(['equity', 'bond'])
    expect(countries[0]?.latestPercentile).toBe(0.72)
    expect(countries[0]?.regime).toBe('high')
    expect(countries[0]?.openAlerts).toBe(1)
  })

  it('normalises the spillover network', () => {
    const payload = normaliseSpilloverPayload({
      scope: 'CN',
      nodes: ['equity', 'bond'],
      matrix: [
        [0.9, 0.1],
        [0.2, 0.8],
      ],
      total_spillout: { equity: 0.2, bond: 0.1 },
      total_spillin: { equity: 0.1, bond: 0.2 },
      net: { equity: 0.1, bond: -0.1 },
      horizon: 10,
      method: 'paper_equation',
      var_order: 5,
      window: ['2011-11-07', '2024-10-18'],
      notes: [],
    })

    expect(payload.nodes).toEqual(['equity', 'bond'])
    expect(payload.matrix[0]?.[1]).toBe(0.1)
    expect(payload.totalSpillout.equity).toBe(0.2)
    expect(payload.net.bond).toBe(-0.1)
    expect(payload.window).toEqual(['2011-11-07', '2024-10-18'])
  })

  it('normalises the alert list', () => {
    const alerts = normaliseAlerts({
      alerts: [
        {
          alert_id: 'CN.composite.p1.2024-10-18',
          country_code: 'CN',
          rule_id: 'composite.p1',
          severity: 'P1',
          state: 'active',
          fired_at: '2024-10-18T08:00:00Z',
          message_key: 'alert.composite_p1',
          message_params: { country: 'CN', threshold: 0.9 },
          attribution: {},
          detail: {},
        },
      ],
    })

    expect(alerts).toHaveLength(1)
    expect(alerts[0]?.severity).toBe('P1')
    expect(alerts[0]?.messageKey).toBe('alert.composite_p1')
    expect(alerts[0]?.messageParams.threshold).toBe(0.9)
  })

  it('normalises the quality report', () => {
    const payload = normaliseQualityPayload({
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
    })

    expect(payload.counts.total).toBe(1)
    expect(payload.series[0]?.seriesId).toBe('equity.pe_ratio')
    expect(payload.series[0]?.checks[0]?.name).toBe('freshness')
  })

  it('normalises the G-SIB list', () => {
    const banks = normaliseGsib({
      banks: [
        { name: 'JP Morgan Chase', bucket: 4, jurisdiction: '', year: 0 },
        { name: 'Bank of America', bucket: 3, jurisdiction: '', year: 0 },
      ],
      count: 2,
      bucket_histogram: { '3': 1, '4': 1 },
    })

    expect(banks).toHaveLength(2)
    expect(banks[0]?.name).toBe('JP Morgan Chase')
    expect(banks[0]?.bucket).toBe(4)
  })

  it('drops a value that is not a number instead of coercing it to zero', () => {
    const payload = normaliseIndexPayload({
      composite: [
        { date: '2024-10-18', value: 0.5 },
        { date: '2024-10-19', value: 'not-a-number' },
      ],
    })
    expect(payload.composite).toHaveLength(1)
  })
})

describe('the request layer', () => {
  it('retries a failed request and then succeeds', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(new Response('boom', { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    const client = new ApiClient({
      baseUrl: 'http://api.test',
      fetchImpl: fetchImpl as unknown as typeof fetch,
      sleep: async () => undefined,
    })

    const result = await client.get<{ ok: boolean }>('/api/v1/health')
    expect(result.ok).toBe(true)
    expect(fetchImpl).toHaveBeenCalledTimes(2)
  })

  it('gives up after the configured number of retries', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('boom', { status: 500 }))

    const client = new ApiClient({
      baseUrl: 'http://api.test',
      retries: 1,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      sleep: async () => undefined,
    })

    await expect(client.get('/api/v1/health')).rejects.toBeInstanceOf(ApiError)
    expect(fetchImpl).toHaveBeenCalledTimes(2)
  })

  it('reports the status code of a failed request', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('missing', { status: 404 }))

    const client = new ApiClient({
      baseUrl: 'http://api.test',
      retries: 0,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      sleep: async () => undefined,
    })

    await expect(client.get('/api/v1/countries')).rejects.toMatchObject({
      status: 404,
      url: 'http://api.test/api/v1/countries',
    })
  })

  it('builds the query string of a request', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))

    const client = new ApiClient({
      baseUrl: 'http://api.test',
      fetchImpl: fetchImpl as unknown as typeof fetch,
      sleep: async () => undefined,
    })

    await client.get('/api/v1/countries/CN/index', { query: { lens: 'percentile' } })
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('http://api.test/api/v1/countries/CN/index?lens=percentile')
  })
})
