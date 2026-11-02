/**
 * The payload shapes the API serves, and the normalisers that turn whatever
 * arrives over the wire into them.
 *
 * The API is language neutral: numbers are numbers, dates are ISO-8601
 * strings and enumerations are stable codes.  The normalisers therefore keep
 * the raw values untouched — no translation happens here, that is the job of
 * the locale catalogue.
 *
 * The normalisers are deliberately forgiving about *shape* (a series may
 * arrive as `[{date, value}]` or as `{dates, values}`) while being strict
 * about *content* (a value that is not a number is dropped, never coerced to
 * zero).
 */

export interface SeriesPoint {
  date: string
  value: number
}

export interface IndicatorWeight {
  code: string
  labelKey?: string
  weight: number
  unit?: string
  direction?: string
}

export interface MarketIndexSeries {
  code: string
  labelKey?: string
  weight?: number
  points: SeriesPoint[]
  indicators: IndicatorWeight[]
}

export interface RegimePoint {
  date: string
  regime: string
  probabilityModerate: number
  probabilityHigh: number
}

export interface RegimeSeries {
  points: RegimePoint[]
  params: Record<string, number | string | boolean>
}

export interface CountryIndexPayload {
  countryCode: string
  asOf: string | null
  /**
   * How the country index is built: `mbsed` (synthesised from sub-market
   * indices) or `official_index` (a published official stress index).
   */
  profile: string
  /**
   * What this run is able to answer.  A capability is absent either because
   * the profile does not have that decomposition at all, or because the
   * computation failed in this run — the run warnings tell the two apart.
   */
  capabilities: Record<string, boolean>
  composite: SeriesPoint[]
  percentile: SeriesPoint[]
  deviation: SeriesPoint[]
  marketIndices: MarketIndexSeries[]
  regime: RegimeSeries
  warnings: string[]
}

export interface SpilloverPayload {
  scope: string
  nodes: string[]
  matrix: number[][]
  totalSpillout: Record<string, number>
  totalSpillin: Record<string, number>
  net: Record<string, number>
  horizon: number
  method: string
  /** The estimator the artefact publishes as its default. */
  defaultMethod: string
  /** Every estimator the artefact publishes — they are not interchangeable. */
  availableMethods: string[]
  /** False when this economy has no spillover network by construction. */
  available: boolean
  /** Why the network is absent, when it is: `not_applicable` or `unavailable`. */
  unavailableReason: string | null
  window: [string, string] | null
  notes: string[]
  varOrder: number | null
}

export interface AlertPayload {
  alertId: string
  countryCode: string
  ruleId: string
  severity: string
  state: string
  firedAt: string | null
  messageKey: string
  messageParams: Record<string, unknown>
  attribution: Record<string, unknown>
  detail: Record<string, unknown>
}

export interface QualityCheckPayload {
  name: string
  passed: boolean
  severity: string
  measured: string | number | null
  threshold: string | number | null
  message: string
}

export interface SeriesQualityPayload {
  seriesId: string
  adapter: string
  countryCode: string
  severity: string
  passed: boolean
  observations: number
  firstDate: string | null
  lastDate: string | null
  checks: QualityCheckPayload[]
}

export interface QualityPayload {
  generatedAt: string | null
  passed: boolean
  counts: { total: number; ok: number; warning: number; failure: number }
  series: SeriesQualityPayload[]
}

export interface CountrySummary {
  code: string
  nameEn: string
  nameLocal: string
  currency: string
  timezone: string
  locale: string
  enabled: boolean
  asOf: string | null
  cissArea: string | null
  /** `mbsed` or `official_index` — see {@link CountryIndexPayload.profile}. */
  profile: string
  capabilities: Record<string, boolean>
  /** The market codes the country index is built from. */
  markets: string[]
  latestPercentile: number | null
  latestDeviation: number | null
  regime: string | null
  probabilityHigh: number | null
  openAlerts: number
}

export interface GsibEntry {
  name: string
  countryCode: string
  bucket: string | number | null
  score: number | null
}

/* ------------------------------------------------------------------ */
/* Primitive helpers                                                   */
/* ------------------------------------------------------------------ */

export function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

export function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return fallback
}

export function asNumber(value: unknown, fallback = Number.NaN): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return fallback
}

export function asNullableNumber(value: unknown): number | null {
  const parsed = asNumber(value, Number.NaN)
  return Number.isFinite(parsed) ? parsed : null
}

function asNumberMap(value: unknown): Record<string, number> {
  const result: Record<string, number> = {}
  for (const [key, item] of Object.entries(asRecord(value))) {
    const parsed = asNumber(item, Number.NaN)
    if (Number.isFinite(parsed)) {
      result[key] = parsed
    }
  }
  return result
}

/** Normalise a `{capability: boolean}` map, keeping only real booleans. */
export function asBooleanMap(value: unknown): Record<string, boolean> {
  const result: Record<string, boolean> = {}
  for (const [key, item] of Object.entries(asRecord(value))) {
    if (typeof item === 'boolean') {
      result[key] = item
    }
  }
  return result
}

/* ------------------------------------------------------------------ */
/* Series                                                              */
/* ------------------------------------------------------------------ */

/** Normalise `[{date, value}]` into the internal point list. */
export function normalisePoints(raw: unknown): SeriesPoint[] {
  const points: SeriesPoint[] = []
  for (const item of asArray(raw)) {
    const record = asRecord(item)
    const date = asString(record.date ?? record.x ?? record.time)
    const value = asNumber(record.value ?? record.y)
    if (date && Number.isFinite(value)) {
      points.push({ date, value })
    }
  }
  return points
}

/** Normalise the `{dates, values}` pair shape into the internal point list. */
export function normalisePointPairs(raw: unknown): SeriesPoint[] {
  const record = asRecord(raw)
  const dates = asArray(record.dates).map((item) => asString(item))
  const values = asArray(record.values).map((item) => asNumber(item))
  const points: SeriesPoint[] = []
  const length = Math.min(dates.length, values.length)
  for (let index = 0; index < length; index += 1) {
    const date = dates[index] as string
    const value = values[index] as number
    if (date && Number.isFinite(value)) {
      points.push({ date, value })
    }
  }
  return points
}

/** Accept either supported shape for a single series. */
export function normaliseSeries(raw: unknown): SeriesPoint[] {
  const points = normalisePoints(raw)
  if (points.length > 0) {
    return points
  }
  return normalisePointPairs(raw)
}

function normaliseIndicators(raw: unknown): IndicatorWeight[] {
  const record = asRecord(raw)
  const weights = asNumberMap(record.weights)
  const result: IndicatorWeight[] = []

  for (const item of asArray(record.indicators ?? record.indicator_weights)) {
    if (typeof item === 'string') {
      const code = item.includes('.') ? (item.split('.').pop() as string) : item
      result.push({
        code,
        labelKey: item.includes('.') ? `indicator.${code}` : undefined,
        weight: asNumber(weights[item], 0),
      })
      continue
    }
    const entry = asRecord(item)
    const code = asString(entry.code ?? entry.indicator)
    if (!code) {
      continue
    }
    result.push({
      code,
      labelKey: asString(entry.label_key) || undefined,
      weight: asNumber(entry.weight, 0),
      unit: asString(entry.unit) || undefined,
      direction: asString(entry.direction) || undefined,
    })
  }

  // A bare `{code: weight}` map is also accepted.
  if (result.length === 0) {
    for (const [key, value] of Object.entries(weights)) {
      const code = key.includes('.') ? (key.split('.').pop() as string) : key
      result.push({ code, labelKey: `indicator.${code}`, weight: value })
    }
  }

  return result
}

/** Normalise the `market_indices` block into one entry per market. */
export function normaliseMarketIndices(raw: unknown): MarketIndexSeries[] {
  const record = asRecord(raw)
  const result: MarketIndexSeries[] = []

  // Shape (a): { dates: [...], series: { code: [...] } }
  if (isPlainObject(record.series)) {
    const dates = asArray(record.dates).map((item) => asString(item))
    for (const [code, values] of Object.entries(asRecord(record.series))) {
      const points: SeriesPoint[] = []
      const numbers = asArray(values).map((item) => asNumber(item))
      const length = Math.min(dates.length, numbers.length)
      for (let index = 0; index < length; index += 1) {
        const date = dates[index] as string
        const value = numbers[index] as number
        if (date && Number.isFinite(value)) {
          points.push({ date, value })
        }
      }
      result.push({ code, points, indicators: [] })
    }
    return result
  }

  // Shape (b): [{ code, dates, values }]
  if (Array.isArray(raw)) {
    for (const item of raw) {
      const entry = asRecord(item)
      const code = asString(entry.code ?? entry.market)
      if (!code) {
        continue
      }
      result.push({
        code,
        labelKey: asString(entry.label_key) || undefined,
        weight: asNullableNumber(entry.weight) ?? undefined,
        points: normaliseSeries(entry),
        indicators: normaliseIndicators(entry),
      })
    }
    return result
  }

  // Shape (c): { code: { dates, values } } or { code: [{ date, value }] }
  for (const [code, value] of Object.entries(record)) {
    const entry = asRecord(value)
    const dates = asArray(entry.dates).map((item) => asString(item))
    const numbers = asArray(entry.values).map((item) => asNumber(item))
    const points: SeriesPoint[] = []
    if (dates.length > 0) {
      const length = Math.min(dates.length, numbers.length)
      for (let index = 0; index < length; index += 1) {
        const date = dates[index] as string
        const number = numbers[index] as number
        if (date && Number.isFinite(number)) {
          points.push({ date, value: number })
        }
      }
    } else {
      // The API serves the market indices as `{code: [{date, value}]}`.
      points.push(...normalisePoints(value))
    }
    result.push({
      code,
      labelKey: asString(entry.label_key) || undefined,
      weight: asNullableNumber(entry.weight) ?? undefined,
      points,
      indicators: normaliseIndicators(entry),
    })
  }
  return result
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Normalise the `regime` block into per-date labels and probabilities. */
export function normaliseRegime(raw: unknown): RegimeSeries {
  const record = asRecord(raw)
  const points: RegimePoint[] = []

  const dates = asArray(record.dates).map((item) => asString(item))
  const labels = asArray(record.labels).map((item) => asString(item))
  const moderate = asArray(record.probability_moderate).map((item) => asNumber(item, 0))
  const high = asArray(record.probability_high).map((item) => asNumber(item, 0))

  if (dates.length > 0) {
    const length = Math.min(
      dates.length,
      Math.max(labels.length, moderate.length, high.length),
    )
    for (let index = 0; index < length; index += 1) {
      const date = dates[index] as string
      if (!date) {
        continue
      }
      points.push({
        date,
        regime: asString(labels[index]),
        probabilityModerate: asNumber(moderate[index], 0),
        probabilityHigh: asNumber(high[index], 0),
      })
    }
  } else {
    for (const item of asArray(raw)) {
      const entry = asRecord(item)
      const date = asString(entry.date)
      if (!date) {
        continue
      }
      points.push({
        date,
        regime: asString(entry.regime),
        probabilityModerate: asNumber(entry.probability_moderate, 0),
        probabilityHigh: asNumber(entry.probability_high, 0),
      })
    }
  }

  const params: Record<string, number | string | boolean> = {}
  for (const [key, value] of Object.entries(asRecord(record.params))) {
    if (typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean') {
      params[key] = value
    }
  }

  return { points, params }
}

/** Normalise the payload of `GET /countries/{code}/index`. */
export function normaliseIndexPayload(raw: unknown, fallbackCode = ''): CountryIndexPayload {
  const record = asRecord(raw)
  const marketBlock = record.market_indices ?? record.markets ?? record.market_index
  return {
    countryCode: asString(record.country_code) || fallbackCode,
    asOf: asString(record.as_of) || null,
    profile: asString(record.profile, 'mbsed'),
    capabilities: asBooleanMap(record.capabilities),
    composite: normaliseSeries(record.composite),
    percentile: normaliseSeries(record.percentile),
    deviation: normaliseSeries(record.deviation),
    marketIndices: normaliseMarketIndices(marketBlock),
    regime: normaliseRegime(record.regime),
    warnings: asArray(record.warnings).map((item) => asString(item)).filter(Boolean),
  }
}

/* ------------------------------------------------------------------ */
/* Spillover                                                           */
/* ------------------------------------------------------------------ */

/** Normalise the payload of a spillover endpoint. */
export function normaliseSpilloverPayload(raw: unknown): SpilloverPayload {
  const record = asRecord(raw)
  const nodes = asArray(record.nodes).map((item) => asString(item)).filter(Boolean)
  const matrix = asArray(record.matrix).map((row) =>
    asArray(row).map((item) => asNumber(item, 0)),
  )
  const window = asArray(record.window).map((item) => asString(item))
  return {
    scope: asString(record.scope),
    nodes,
    matrix,
    totalSpillout: asNumberMap(record.total_spillout),
    totalSpillin: asNumberMap(record.total_spillin),
    net: asNumberMap(record.net),
    horizon: asNumber(record.horizon, 10),
    method: asString(record.method, 'paper_equation'),
    defaultMethod: asString(record.default_method, asString(record.method, 'paper_equation')),
    availableMethods: asArray(record.available_methods)
      .map((item) => asString(item))
      .filter(Boolean),
    available: record.available !== false,
    unavailableReason: asString(record.unavailable_reason) || null,
    window: window.length === 2 ? [window[0] as string, window[1] as string] : null,
    notes: asArray(record.notes).map((item) => asString(item)).filter(Boolean),
    varOrder: asNullableNumber(record.var_order),
  }
}

/* ------------------------------------------------------------------ */
/* Alerts                                                              */
/* ------------------------------------------------------------------ */

/** Normalise the payload of `GET /countries/{code}/alerts`. */
export function normaliseAlerts(raw: unknown): AlertPayload[] {
  const list = Array.isArray(raw) ? raw : asArray(asRecord(raw).alerts)
  const result: AlertPayload[] = []
  for (const item of list) {
    const entry = asRecord(item)
    result.push({
      alertId: asString(entry.alert_id),
      countryCode: asString(entry.country_code),
      ruleId: asString(entry.rule_id),
      severity: asString(entry.severity, 'P3'),
      state: asString(entry.state, 'active'),
      firedAt: asString(entry.fired_at) || null,
      messageKey: asString(entry.message_key),
      messageParams: asRecord(entry.message_params),
      attribution: asRecord(entry.attribution),
      detail: asRecord(entry.detail),
    })
  }
  return result
}

/* ------------------------------------------------------------------ */
/* Data quality                                                        */
/* ------------------------------------------------------------------ */

/** Normalise the payload of `GET /data-quality/{code}`. */
export function normaliseQualityPayload(raw: unknown): QualityPayload {
  const record = asRecord(raw)
  const counts = asRecord(record.counts)
  const series: SeriesQualityPayload[] = []
  for (const item of asArray(record.series)) {
    const entry = asRecord(item)
    const checks: QualityCheckPayload[] = []
    for (const rawCheck of asArray(entry.checks)) {
      const check = asRecord(rawCheck)
      checks.push({
        name: asString(check.name),
        passed: check.passed === true,
        severity: asString(check.severity, 'ok'),
        measured: (check.measured ?? null) as string | number | null,
        threshold: (check.threshold ?? null) as string | number | null,
        message: asString(check.message),
      })
    }
    series.push({
      seriesId: asString(entry.series_id),
      adapter: asString(entry.adapter),
      countryCode: asString(entry.country_code),
      severity: asString(entry.severity, 'ok'),
      passed: entry.passed === true,
      observations: asNumber(entry.observations, 0),
      firstDate: asString(entry.first_date) || null,
      lastDate: asString(entry.last_date) || null,
      checks,
    })
  }
  return {
    generatedAt: asString(record.generated_at) || null,
    passed: record.passed === true,
    counts: {
      total: asNumber(counts.total, series.length),
      ok: asNumber(counts.ok, 0),
      warning: asNumber(counts.warning, 0),
      failure: asNumber(counts.failure, 0),
    },
    series,
  }
}

/* ------------------------------------------------------------------ */
/* Countries and G-SIBs                                                */
/* ------------------------------------------------------------------ */

/** Normalise the payload of `GET /countries`. */
export function normaliseCountries(raw: unknown): CountrySummary[] {
  const list = Array.isArray(raw) ? raw : asArray(asRecord(raw).countries)
  const result: CountrySummary[] = []
  for (const item of list) {
    const entry = asRecord(item)
    const code = asString(entry.code)
    if (!code) {
      continue
    }
    result.push({
      code,
      nameEn: asString(entry.name_en),
      nameLocal: asString(entry.name_local),
      currency: asString(entry.currency),
      timezone: asString(entry.timezone),
      locale: asString(entry.locale),
      enabled: entry.enabled !== false,
      asOf: asString(entry.as_of) || null,
      cissArea: asString(entry.ciss_area) || null,
      profile: asString(entry.profile, 'mbsed'),
      capabilities: asBooleanMap(entry.capabilities),
      markets: asArray(entry.markets).map((item) => asString(item)).filter(Boolean),
      latestPercentile: asNullableNumber(entry.latest_percentile),
      latestDeviation: asNullableNumber(entry.latest_deviation),
      regime: asString(entry.regime) || null,
      probabilityHigh: asNullableNumber(entry.probability_high),
      openAlerts: asNumber(entry.open_alerts, 0),
    })
  }
  return result
}

/** Normalise the payload of `GET /global/gsib`. */
export function normaliseGsib(raw: unknown): GsibEntry[] {
  const list = Array.isArray(raw)
    ? raw
    : asArray(asRecord(raw).gsib ?? asRecord(raw).entries ?? asRecord(raw).banks)
  const result: GsibEntry[] = []
  for (const item of list) {
    if (typeof item === 'string') {
      result.push({ name: item, countryCode: '', bucket: null, score: null })
      continue
    }
    const entry = asRecord(item)
    const name = asString(entry.name ?? entry.bank ?? entry.label)
    if (!name) {
      continue
    }
    const bucket = entry.bucket ?? null
    result.push({
      name,
      countryCode: asString(entry.country_code ?? entry.country),
      bucket:
        typeof bucket === 'number' || typeof bucket === 'string' ? bucket : null,
      score: asNullableNumber(entry.score),
    })
  }
  return result
}
