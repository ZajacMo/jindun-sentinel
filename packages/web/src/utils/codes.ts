/**
 * Mapping from the language-neutral codes used by the API to the message keys
 * of the shared locale catalogue.
 *
 * The API never returns a translated string: it returns a stable code such as
 * `"regime": "high"` or `"severity": "P1"`.  Turning such a code into a label
 * is a pure function of the code, so it lives here — and it is covered by unit
 * tests.
 */

/** The five monitored economies. */
export const COUNTRY_CODES = ['CN', 'US', 'EU', 'GB', 'JP'] as const

export type CountryCode = (typeof COUNTRY_CODES)[number]

/** The three alert severities, most severe first. */
export const SEVERITY_CODES = ['P1', 'P2', 'P3'] as const

export type SeverityCode = (typeof SEVERITY_CODES)[number]

/** The two regime states. */
export const REGIME_CODES = ['moderate', 'high'] as const

export type RegimeCode = (typeof REGIME_CODES)[number]

/** The five market segments. */
export const MARKET_CODES = ['equity', 'bond', 'fx', 'money', 'derivative'] as const

export type MarketCode = (typeof MARKET_CODES)[number]

/** The four spillover estimators implemented by the pipeline. */
export const METHOD_CODES = [
  'paper_equation',
  'sims_structural',
  'dy_generalised',
  'legacy_appendix',
] as const

export type MethodCode = (typeof METHOD_CODES)[number]

/** The two reporting lenses of the composite index. */
export const LENS_CODES = ['percentile', 'deviation'] as const

export type LensCode = (typeof LENS_CODES)[number]

/** The data-quality verdicts. */
export const QUALITY_CODES = ['ok', 'warning', 'failure'] as const

export type QualityCode = (typeof QUALITY_CODES)[number]

function namespaced(namespace: string, code: string): string {
  return `${namespace}.${code}`
}

/** `CN` -> `country.CN` */
export function countryLabelKey(code: string): string {
  return namespaced('country', code)
}

/** `P1` -> `severity.P1` */
export function severityLabelKey(code: string): string {
  return namespaced('severity', code)
}

/** `high` -> `regime.high` */
export function regimeLabelKey(code: string): string {
  return namespaced('regime', code)
}

/** `equity` -> `market.equity` */
export function marketLabelKey(code: string): string {
  return namespaced('market', code)
}

/**
 * `pe` -> `indicator.pe`.
 *
 * An explicit `label_key` coming from the configuration wins, because the
 * pipeline allows an indicator to be labelled with any catalogue key.
 */
export function indicatorLabelKey(code: string, labelKey?: string | null): string {
  if (typeof labelKey === 'string' && labelKey.length > 0) {
    return labelKey
  }
  return namespaced('indicator', code)
}

/** `paper_equation` -> `method.paper_equation` */
export function methodLabelKey(code: string): string {
  return namespaced('method', code)
}

/** `percentile` -> `lens.percentile` */
export function lensLabelKey(code: string): string {
  return namespaced('lens', code)
}

/** `global` -> `scope.global` */
export function scopeLabelKey(code: string): string {
  return namespaced('scope', code)
}

/** `warning` -> `quality.warning` */
export function qualityLabelKey(code: string): string {
  return namespaced('quality', code)
}

/** `pct` -> `unit.pct` */
export function unitLabelKey(code: string): string {
  return namespaced('unit', code)
}

/** The severity of an alert, tolerant of unknown codes. */
export function isSeverityCode(code: unknown): code is SeverityCode {
  return typeof code === 'string' && (SEVERITY_CODES as readonly string[]).includes(code)
}

/** The regime of an observation, tolerant of unknown codes. */
export function isRegimeCode(code: unknown): code is RegimeCode {
  return typeof code === 'string' && (REGIME_CODES as readonly string[]).includes(code)
}

/**
 * The identifier of a node in a spillover network.
 *
 * Cross-market networks use the market codes, cross-country networks use the
 * country codes; both are rendered through the matching catalogue namespace.
 */
export function nodeLabelKey(node: string): string {
  if ((MARKET_CODES as readonly string[]).includes(node)) {
    return marketLabelKey(node)
  }
  if ((COUNTRY_CODES as readonly string[]).includes(node)) {
    return countryLabelKey(node)
  }
  return node
}
