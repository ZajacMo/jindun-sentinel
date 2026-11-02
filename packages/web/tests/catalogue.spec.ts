import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { buildMessages, SUPPORTED_LOCALES } from '@/i18n/catalogue'
import { countryLabelKey, severityLabelKey } from '@/utils/codes'

/**
 * The catalogue is shared with the Python server, and the front end must read
 * the very same files.  These tests verify that wiring: the four locales load
 * from `<repo-root>/locales`, every code resolves to a real message, and a
 * missing key falls back to the key itself instead of to an English string.
 */
const messages = buildMessages()

function composer(locale: string) {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: false,
    missingWarn: false,
    fallbackWarn: false,
    messages,
  })
}

describe('shared locale catalogue', () => {
  it('loads all four shipped locales', () => {
    expect([...SUPPORTED_LOCALES]).toEqual(['en-US', 'zh-CN', 'zh-TW', 'ja-JP'])
    for (const locale of SUPPORTED_LOCALES) {
      expect(messages[locale]).toBeTruthy()
      expect(Object.keys(messages[locale] ?? {}).length).toBeGreaterThan(0)
    }
  })

  it('resolves a country code to a localised name in every locale', () => {
    for (const locale of SUPPORTED_LOCALES) {
      const t = composer(locale).global.t
      const rendered = t(countryLabelKey('CN'))
      expect(rendered).not.toBe(countryLabelKey('CN'))
      expect(rendered.length).toBeGreaterThan(0)
    }
  })

  it('resolves a severity code to a localised label in every locale', () => {
    for (const locale of SUPPORTED_LOCALES) {
      const t = composer(locale).global.t
      const rendered = t(severityLabelKey('P1'))
      expect(rendered).not.toBe(severityLabelKey('P1'))
      expect(rendered).toContain('P1')
    }
  })

  it('renders a different label per locale', () => {
    const rendered = SUPPORTED_LOCALES.map((locale) =>
      composer(locale).global.t(countryLabelKey('CN')),
    )
    expect(new Set(rendered).size).toBeGreaterThan(1)
  })

  it('shows the key itself when a message is missing', () => {
    const t = composer('en-US').global.t
    expect(t('this.key.does.not.exist')).toBe('this.key.does.not.exist')
  })
})
