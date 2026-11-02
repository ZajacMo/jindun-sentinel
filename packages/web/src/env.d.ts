/// <reference types="vite/client" />

declare module 'virtual:jindun-locale-catalogue' {
  /** Locale code -> raw catalogue, as read from `<repo-root>/locales/<locale>.json`. */
  const catalogues: Record<string, Record<string, unknown>>
  export default catalogues
}
