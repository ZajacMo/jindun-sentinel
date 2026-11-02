/**
 * Vite plugin that exposes the shared locale catalogue as a virtual module.
 *
 * The catalogue is a directory of `<locale>.json` files that lives at the
 * repository root ("../../locales" relative to this package).  The same files
 * are read by the Python server through `jindun.i18n`, so reading them here is
 * what keeps the on-screen labels and the server-side messages in sync.
 *
 * The plugin is deliberately forgiving: a missing directory or a malformed
 * file is skipped instead of breaking the build.  A locale without a catalogue
 * simply renders the message keys, which is the intended failure mode.
 *
 * The hook signatures are kept deliberately loose.  The plugin is used both by
 * the Vite build and by Vitest, which bundle different Vite majors; a narrow
 * type would make the plugin incompatible with one of them.
 */
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const VIRTUAL_ID = 'virtual:jindun-locale-catalogue'
const RESOLVED_ID = `\0${VIRTUAL_ID}`

export interface LocaleCataloguePluginOptions {
  /** Absolute path of the directory that holds the `<locale>.json` files. */
  dir: string
}

/** Read every `<locale>.json` file in `dir`; unreadable files are skipped. */
export function readCatalogues(dir: string): Record<string, Record<string, unknown>> {
  const catalogues: Record<string, Record<string, unknown>> = {}
  if (!existsSync(dir)) {
    return catalogues
  }
  for (const entry of readdirSync(dir)) {
    if (!entry.endsWith('.json')) {
      continue
    }
    try {
      const parsed: unknown = JSON.parse(readFileSync(join(dir, entry), 'utf-8'))
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        catalogues[entry.slice(0, -'.json'.length)] = parsed as Record<string, unknown>
      }
    } catch {
      // A malformed catalogue must not take the whole build down.
    }
  }
  return catalogues
}

interface ModuleGraph {
  getModuleById(id: string): { id: string } | undefined
  invalidateModule(module: { id: string }): void
}

export function localeCataloguePlugin(options: LocaleCataloguePluginOptions) {
  const { dir } = options

  return {
    name: 'jindun-locale-catalogue',
    enforce: 'pre' as const,

    resolveId(id: string): string | null {
      return id === VIRTUAL_ID ? RESOLVED_ID : null
    },

    load(id: string): string | null {
      if (id !== RESOLVED_ID) {
        return null
      }
      return `export default ${JSON.stringify(readCatalogues(dir))}\n`
    },

    configureServer(server: unknown): void {
      const watcher = (server as { watcher?: { add?: (path: string) => void } } | undefined)?.watcher
      if (watcher && typeof watcher.add === 'function' && existsSync(dir)) {
        watcher.add(dir)
      }
    },

    hotUpdate(context: unknown): void {
      const update = context as
        | {
            file?: string
            server?: { moduleGraph?: ModuleGraph }
          }
        | undefined
      if (!update?.file?.startsWith(dir)) {
        return
      }
      const moduleGraph = update.server?.moduleGraph
      const module = moduleGraph?.getModuleById(RESOLVED_ID)
      if (module && moduleGraph) {
        moduleGraph.invalidateModule(module)
      }
    },
  }
}
