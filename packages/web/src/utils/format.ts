/**
 * Locale-aware formatting helpers.
 *
 * Every number and every date that reaches the screen goes through `Intl`, so
 * the rendering follows the active locale: `1,234.5` in en-US, `1,234.5` in
 * zh-CN, `1,234.5` in ja-JP, and dates such as "Oct 18, 2024" versus
 * "2024年10月18日".
 */

/** A dash is rendered wherever a number is missing. */
const MISSING = '—'

export function formatNumber(
  value: number | null | undefined,
  locale: string,
  options: Intl.NumberFormatOptions = {},
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return MISSING
  }
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: 2,
    ...options,
  }).format(value)
}

/** Format a ratio in `[0, 1]` as a percentage. */
export function formatPercent(
  value: number | null | undefined,
  locale: string,
  options: Intl.NumberFormatOptions = {},
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return MISSING
  }
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 1,
    ...options,
  }).format(value)
}

/** Format a share (a spillover matrix entry) as a percentage. */
export function formatShare(
  value: number | null | undefined,
  locale: string,
  digits = 2,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return MISSING
  }
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === '') {
    return null
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  const parsed = typeof value === 'number' ? new Date(value) : new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

/**
 * Format an ISO-8601 date with the date style of the active locale.
 *
 * The pipeline emits plain ISO dates; the API never pre-formats them.
 */
export function formatDate(
  value: string | number | Date | null | undefined,
  locale: string,
  style: 'short' | 'medium' | 'long' = 'medium',
): string {
  const date = toDate(value)
  if (!date) {
    return MISSING
  }
  return new Intl.DateTimeFormat(locale, { dateStyle: style }).format(date)
}

/** Format an ISO-8601 timestamp with both a date and a time. */
export function formatDateTime(
  value: string | number | Date | null | undefined,
  locale: string,
  style: 'short' | 'medium' = 'medium',
): string {
  const date = toDate(value)
  if (!date) {
    return MISSING
  }
  return new Intl.DateTimeFormat(locale, {
    dateStyle: style,
    timeStyle: 'short',
  }).format(date)
}

/** Format a duration expressed in days. */
export function formatDays(
  value: number | null | undefined,
  locale: string,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return MISSING
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)
}

export { MISSING }
