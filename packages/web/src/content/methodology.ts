/**
 * The methodology documents.
 *
 * The notes live in `docs/methodology/` at the repository root and are read
 * at build time through a raw import, so the documentation that is shown is
 * the documentation that is in the repository — there is no second copy.
 */
const modules = import.meta.glob('../../../../docs/methodology/*.md', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

export interface MethodologyDocument {
  /** The file name without its extension. */
  id: string
  /** The first level-one heading of the document, when it has one. */
  title: string | null
  /** The raw Markdown source. */
  source: string
}

export const methodologyDocuments: MethodologyDocument[] = Object.entries(modules)
  .map(([path, source]) => {
    const id = (path.split('/').pop() ?? path).replace(/\.md$/, '')
    const title = /^#\s+(.+)$/m.exec(source)
    return { id, title: title ? (title[1] as string).trim() : null, source }
  })
  .sort((left, right) => left.id.localeCompare(right.id))

export const hasMethodologyDocuments = methodologyDocuments.length > 0
