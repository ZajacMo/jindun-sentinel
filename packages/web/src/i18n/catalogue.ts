/**
 * Access to the shared locale catalogue.
 *
 * The catalogue lives at `<repo-root>/locales/<locale>.json` and is read at
 * build time by the `jindun-locale-catalogue` Vite plugin.  Those files are the
 * single source of truth for every translatable string in the application —
 * the Python server reads the very same files through `jindun.i18n`.
 *
 * The catalogues are stored either flat (`{"app.name": "JinDun Sentinel"}`) or
 * nested (`{"app": {"name": "JinDun Sentinel"}}`); both are normalised into the
 * nested shape vue-i18n expects.
 */
import rawCatalogues from 'virtual:jindun-locale-catalogue'

export const SUPPORTED_LOCALES = ['en-US', 'zh-CN', 'zh-TW', 'ja-JP'] as const

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: SupportedLocale = 'en-US'

/** All four shipped locales are left-to-right. */
export const LOCALE_DIRECTION: Record<SupportedLocale, 'ltr' | 'rtl'> = {
  'en-US': 'ltr',
  'zh-CN': 'ltr',
  'zh-TW': 'ltr',
  'ja-JP': 'ltr',
}

/** The display name of a locale is a property of the locale, not a message. */
export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  'en-US': 'English',
  'zh-CN': '简体中文',
  'zh-TW': '繁體中文',
  'ja-JP': '日本語',
}

/** A nested message tree, as consumed by vue-i18n. */
export interface MessageTree {
  [key: string]: string | MessageTree
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function setPath(tree: MessageTree, segments: string[], value: string | MessageTree): void {
  let node = tree
  for (let index = 0; index < segments.length - 1; index += 1) {
    const segment = segments[index] as string
    const child = node[segment]
    if (!isPlainObject(child)) {
      const created: MessageTree = {}
      node[segment] = created
      node = created
    } else {
      node = child as MessageTree
    }
  }
  const last = segments[segments.length - 1] as string
  const existing = node[last]
  if (isPlainObject(existing) && isPlainObject(value)) {
    node[last] = { ...existing, ...value }
  } else {
    node[last] = value
  }
}

/**
 * Normalise a raw catalogue into a nested message tree.
 *
 * Dotted keys are expanded into namespaces, nested objects are merged, and
 * anything that is not a string is dropped.
 */
export function normaliseCatalogue(raw: Record<string, unknown>): MessageTree {
  const tree: MessageTree = {}
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === 'string') {
      setPath(tree, key.split('.'), value)
    } else if (isPlainObject(value)) {
      setPath(tree, key.split('.'), normaliseCatalogue(value))
    }
  }
  return tree
}

/** Build the vue-i18n `messages` object from the raw catalogues. */
export function buildMessages(
  catalogues: Record<string, Record<string, unknown>> = rawCatalogues,
): Record<string, MessageTree> {
  const messages: Record<string, MessageTree> = {}
  for (const locale of SUPPORTED_LOCALES) {
    messages[locale] = normaliseCatalogue(catalogues[locale] ?? {})
  }
  return messages
}

export function isSupportedLocale(value: unknown): value is SupportedLocale {
  return typeof value === 'string' && (SUPPORTED_LOCALES as readonly string[]).includes(value)
}
