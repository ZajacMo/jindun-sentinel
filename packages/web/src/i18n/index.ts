/**
 * The vue-i18n instance.
 *
 * `legacy: false` selects the Composition API, which is what every component
 * in this project uses.  `fallbackLocale: false` is deliberate: a message that
 * is missing from the catalogue renders as its own key, so a translation gap is
 * loud instead of silently showing an English string in another language.
 */
import { createI18n } from 'vue-i18n'
import { buildMessages, DEFAULT_LOCALE } from './catalogue'
import type { SupportedLocale } from './catalogue'

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: DEFAULT_LOCALE,
  fallbackLocale: false,
  missingWarn: false,
  fallbackWarn: false,
  messages: buildMessages(),
})

/** Switch the active locale of the global composer. */
export function setActiveLocale(locale: SupportedLocale): void {
  i18n.global.locale.value = locale
}

export function activeLocale(): SupportedLocale {
  return i18n.global.locale.value as SupportedLocale
}

export type { SupportedLocale }
