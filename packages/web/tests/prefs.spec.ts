import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePrefsStore } from '@/stores/prefs'

/**
 * The language switcher has to update the document, not only the messages:
 * `<html lang>` drives the line-height cascade of the stylesheet and `dir`
 * drives the text direction.
 */
describe('preferences store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    document.documentElement.removeAttribute('lang')
    document.documentElement.removeAttribute('dir')
    document.documentElement.classList.remove('dark')
  })

  it('writes the locale and the direction onto the document element', () => {
    const prefs = usePrefsStore()

    prefs.setLocale('ja-JP')
    expect(document.documentElement.getAttribute('lang')).toBe('ja-JP')
    expect(document.documentElement.getAttribute('dir')).toBe('ltr')

    prefs.setLocale('zh-CN')
    expect(document.documentElement.getAttribute('lang')).toBe('zh-CN')
    expect(document.documentElement.getAttribute('dir')).toBe('ltr')
  })

  it('toggles the dark theme on the document element', () => {
    const prefs = usePrefsStore()

    expect(prefs.theme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    prefs.toggleTheme()
    expect(prefs.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    prefs.toggleTheme()
    expect(prefs.theme).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('keeps the selected country and the reporting lens', () => {
    const prefs = usePrefsStore()

    prefs.setCountry('JP')
    prefs.setLens('deviation')

    expect(prefs.countryCode).toBe('JP')
    expect(prefs.lens).toBe('deviation')
  })
})
