/**
 * User preferences that are shared across the whole application: the active
 * locale, the colour theme, the selected economy and the reporting lens.
 *
 * The state is persisted in `localStorage` so a reload keeps the workspace
 * exactly as the analyst left it.
 */
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { LOCALE_DIRECTION, isSupportedLocale } from '@/i18n/catalogue'
import type { SupportedLocale } from '@/i18n/catalogue'
import { setActiveLocale } from '@/i18n'

export type ThemeName = 'light' | 'dark'
export type LensName = 'percentile' | 'deviation'

const STORAGE_KEY = 'jindun.sentinel.prefs'

interface PersistedPrefs {
  locale?: string
  theme?: string
  countryCode?: string
  lens?: string
}

function readPersisted(): PersistedPrefs {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY)
    if (!raw) {
      return {}
    }
    const parsed: unknown = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? (parsed as PersistedPrefs) : {}
  } catch {
    return {}
  }
}

function persist(value: PersistedPrefs): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch {
    // A browser with storage disabled is not an error worth surfacing.
  }
}

export const usePrefsStore = defineStore('prefs', () => {
  const persisted = readPersisted()

  const locale = ref<SupportedLocale>(
    isSupportedLocale(persisted.locale) ? persisted.locale : 'en-US',
  )
  const theme = ref<ThemeName>(persisted.theme === 'dark' ? 'dark' : 'light')
  const countryCode = ref<string>(persisted.countryCode ?? 'CN')
  const lens = ref<LensName>(persisted.lens === 'deviation' ? 'deviation' : 'percentile')

  const direction = computed<'ltr' | 'rtl'>(() => LOCALE_DIRECTION[locale.value])

  function applyDocumentState(): void {
    const root = globalThis.document?.documentElement
    if (!root) {
      return
    }
    root.setAttribute('lang', locale.value)
    root.setAttribute('dir', direction.value)
    root.classList.toggle('dark', theme.value === 'dark')
  }

  function setLocale(next: SupportedLocale): void {
    locale.value = next
    setActiveLocale(next)
    applyDocumentState()
  }

  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    applyDocumentState()
  }

  function setCountry(code: string): void {
    countryCode.value = code
  }

  function setLens(next: LensName): void {
    lens.value = next
  }

  watch(
    [locale, theme],
    () => {
      applyDocumentState()
      persist({
        locale: locale.value,
        theme: theme.value,
        countryCode: countryCode.value,
        lens: lens.value,
      })
    },
    { immediate: true },
  )

  watch([countryCode, lens], () => {
    persist({
      locale: locale.value,
      theme: theme.value,
      countryCode: countryCode.value,
      lens: lens.value,
    })
  })

  setActiveLocale(locale.value)
  applyDocumentState()

  return {
    locale,
    theme,
    countryCode,
    lens,
    direction,
    setLocale,
    toggleTheme,
    setCountry,
    setLens,
  }
})
