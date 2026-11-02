import { describe, expect, it } from 'vitest'
import {
  formatDate,
  formatDateTime,
  formatDays,
  formatNumber,
  formatPercent,
  formatShare,
} from '@/utils/format'

/**
 * Numbers and dates are rendered with `Intl`, so they follow the active
 * locale.  A hard-coded "YYYY-MM-DD" or "1,234.5" would be wrong in three of
 * the four shipped locales.
 */
describe('locale aware formatting', () => {
  it('formats a number with the separators of the locale', () => {
    expect(formatNumber(1234.5, 'en-US')).toBe('1,234.5')
    expect(formatNumber(1234.5, 'de-DE')).toBe('1.234,5')
    expect(formatNumber(1234.5, 'ja-JP')).toBe('1,234.5')
  })

  it('respects the requested number of fraction digits', () => {
    expect(formatNumber(0.123456, 'en-US', { maximumFractionDigits: 2 })).toBe('0.12')
    expect(formatNumber(0.123456, 'en-US', { maximumFractionDigits: 4 })).toBe('0.1235')
  })

  it('formats a ratio as a percentage', () => {
    expect(formatPercent(0.1234, 'en-US')).toBe('12.3%')
    // German puts a (no-break) space between the number and the sign.
    expect(formatPercent(0.1234, 'de-DE')).toMatch(/^12,3\s*%$/u)
    expect(formatPercent(0.1234, 'zh-CN')).toBe('12.3%')
  })

  it('formats a spillover share with a fixed precision', () => {
    expect(formatShare(0.971463, 'en-US')).toBe('97.15%')
    expect(formatShare(0.5, 'en-US', 0)).toBe('50%')
  })

  it('formats a date the way the locale writes it', () => {
    expect(formatDate('2024-10-18', 'en-US')).toBe('Oct 18, 2024')
    expect(formatDate('2024-10-18', 'zh-CN')).toBe('2024年10月18日')
    expect(formatDate('2024-10-18', 'ja-JP')).toBe('2024/10/18')
  })

  it('does not use the ISO layout for every locale', () => {
    const rendered = ['en-US', 'zh-CN', 'zh-TW', 'ja-JP'].map((locale) =>
      formatDate('2024-10-18', locale),
    )
    expect(new Set(rendered).size).toBeGreaterThan(1)
    expect(rendered).not.toContain('2024-10-18')
  })

  it('formats a timestamp with a date and a time', () => {
    expect(formatDateTime('2024-10-18T08:00:00Z', 'en-US')).toContain('Oct 18, 2024')
    expect(formatDateTime('2024-10-18T08:00:00Z', 'en-US')).toMatch(/\d{1,2}:\d{2}/)
  })

  it('renders a dash for a missing number', () => {
    expect(formatNumber(null, 'en-US')).toBe('—')
    expect(formatNumber(undefined, 'en-US')).toBe('—')
    expect(formatNumber(Number.NaN, 'en-US')).toBe('—')
    expect(formatPercent(null, 'en-US')).toBe('—')
    expect(formatDate(null, 'en-US')).toBe('—')
    expect(formatDate('not-a-date', 'en-US')).toBe('—')
  })

  it('formats a duration in days', () => {
    expect(formatDays(3, 'en-US')).toBe('3')
    expect(formatDays(3.5, 'en-US')).toBe('3.5')
  })
})
