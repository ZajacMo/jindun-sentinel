/**
 * A small Markdown renderer.
 *
 * The methodology notes are read from the repository at build time and are
 * plain prose with headings, tables, lists, code blocks and a little inline
 * formatting.  Rendering them with a focused renderer keeps the dependency
 * set of the front end exactly as specified and keeps the output predictable.
 *
 * The renderer escapes every piece of source text before it is turned into
 * markup; only the formatting this module produces itself is emitted as HTML.
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Render the inline markup of a single line of text. */
export function renderInline(text: string): string {
  let output = escapeHtml(text)

  // Code spans are extracted first so their content is not formatted.
  const codeSpans: string[] = []
  output = output.replace(/`([^`]+)`/g, (_match, code: string) => {
    codeSpans.push(code)
    return `\u0000${codeSpans.length - 1}\u0000`
  })

  output = output.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  )
  output = output.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  output = output.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  output = output.replace(/(^|[^*\w])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  output = output.replace(/~~([^~]+)~~/g, '<del>$1</del>')
  output = output.replace(/\u0000(\d+)\u0000/g, (_match, index: string) => {
    return `<code>${codeSpans[Number(index)] ?? ''}</code>`
  })

  return output
}

function isTableSeparator(line: string): boolean {
  return /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(line) && line.includes('-')
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return trimmed.split('|').map((cell) => cell.trim())
}

/** Render a Markdown document into an HTML fragment. */
export function renderMarkdown(source: string): string {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const html: string[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index] as string

    if (line.trim() === '') {
      index += 1
      continue
    }

    // Fenced code block.
    const fence = /^\s*(```|~~~)\s*([\w+-]*)\s*$/.exec(line)
    if (fence) {
      const marker = fence[1] as string
      const language = fence[2] as string
      const body: string[] = []
      index += 1
      while (index < lines.length && !(lines[index] as string).trimStart().startsWith(marker)) {
        body.push(lines[index] as string)
        index += 1
      }
      index += 1
      const attribute = language ? ` class="language-${language}"` : ''
      html.push(`<pre><code${attribute}>${escapeHtml(body.join('\n'))}</code></pre>`)
      continue
    }

    // Heading.
    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading) {
      const level = (heading[1] as string).length
      html.push(`<h${level}>${renderInline(heading[2] as string)}</h${level}>`)
      index += 1
      continue
    }

    // Horizontal rule.
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) {
      html.push('<hr />')
      index += 1
      continue
    }

    // Table.
    if (
      line.trim().startsWith('|') &&
      index + 1 < lines.length &&
      isTableSeparator(lines[index + 1] as string)
    ) {
      const header = splitTableRow(line)
      index += 2
      const rows: string[][] = []
      while (index < lines.length && (lines[index] as string).trim().startsWith('|')) {
        rows.push(splitTableRow(lines[index] as string))
        index += 1
      }
      const head = header
        .map((cell) => `<th>${renderInline(cell)}</th>`)
        .join('')
      const body = rows
        .map(
          (row) =>
            `<tr>${header
              .map((_cell, column) => `<td>${renderInline(row[column] ?? '')}</td>`)
              .join('')}</tr>`,
        )
        .join('')
      html.push(`<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`)
      continue
    }

    // Blockquote.
    if (/^\s*>\s?/.test(line)) {
      const body: string[] = []
      while (index < lines.length && /^\s*>\s?/.test(lines[index] as string)) {
        body.push((lines[index] as string).replace(/^\s*>\s?/, ''))
        index += 1
      }
      html.push(`<blockquote>${renderMarkdown(body.join('\n'))}</blockquote>`)
      continue
    }

    // Lists.
    const listMatch = /^\s*([-*+]|\d+[.)])\s+/.exec(line)
    if (listMatch) {
      const ordered = /\d/.test(listMatch[1] as string)
      const items: string[] = []
      while (index < lines.length) {
        const current = lines[index] as string
        const item = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(current)
        if (!item) {
          break
        }
        items.push(`<li>${renderInline(item[2] as string)}</li>`)
        index += 1
      }
      const tag = ordered ? 'ol' : 'ul'
      html.push(`<${tag}>${items.join('')}</${tag}>`)
      continue
    }

    // Paragraph.
    const paragraph: string[] = []
    while (index < lines.length) {
      const current = lines[index] as string
      if (
        current.trim() === '' ||
        /^(#{1,6})\s+/.test(current) ||
        /^\s*(```|~~~)/.test(current) ||
        /^\s*([-*+]|\d+[.)])\s+/.test(current) ||
        /^\s*>\s?/.test(current)
      ) {
        break
      }
      paragraph.push(current.trim())
      index += 1
    }
    html.push(`<p>${renderInline(paragraph.join(' '))}</p>`)
  }

  return html.join('\n')
}

/** The first level-one heading of a document, used as its title. */
export function extractTitle(source: string): string | null {
  const match = /^#\s+(.+)$/m.exec(source)
  return match ? (match[1] as string).trim() : null
}
