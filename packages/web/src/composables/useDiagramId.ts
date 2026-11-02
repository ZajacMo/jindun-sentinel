/**
 * A unique DOM id per diagram instance.
 *
 * SVG markers are referenced by fragment identifier, and those identifiers are
 * document wide.  Two diagrams on the same page would otherwise share (and
 * overwrite) each other's arrow heads, so every instance gets its own prefix.
 */
let counter = 0

export function useDiagramId(prefix: string): string {
  counter += 1
  return `jd-${prefix}-${counter}`
}
