import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * The typography rules are part of the deliverable: the line height has to
 * follow the script of the active locale, and the font stack may only be
 * declared once, in the global stylesheet.
 */
const baseCss = readFileSync(resolve(process.cwd(), 'src/styles/base.css'), 'utf-8')
const tokenCss = readFileSync(resolve(process.cwd(), 'src/styles/tokens.css'), 'utf-8')

describe('global stylesheet', () => {
  it('gives Latin script a line height of 1.5', () => {
    expect(baseCss).toMatch(/html\s*\{[^}]*line-height:\s*1\.5\s*;/)
  })

  it('gives Chinese a line height of 1.7', () => {
    expect(baseCss).toMatch(/html\[lang='zh-CN'\]\s*\{[^}]*line-height:\s*1\.7\s*;/)
    expect(baseCss).toMatch(/html\[lang='zh-TW'\]\s*\{[^}]*line-height:\s*1\.7\s*;/)
  })

  it('gives Japanese a line height of 1.8', () => {
    expect(baseCss).toMatch(/html\[lang='ja-JP'\]\s*\{[^}]*line-height:\s*1\.8\s*;/)
  })

  it('declares the font stack once, as a custom property', () => {
    expect(tokenCss).toContain('--jd-font-stack')
    for (const family of [
      'Noto Sans SC',
      'Noto Sans TC',
      'Noto Sans JP',
      'PingFang SC',
      'Hiragino Sans',
      'Microsoft YaHei',
    ]) {
      expect(tokenCss).toContain(family)
    }
    expect(tokenCss).toContain('system-ui')
    expect(baseCss).toContain('font-family: var(--jd-font-stack)')
  })

  it('uses tabular numerals for the numeric columns', () => {
    expect(baseCss).toContain('font-variant-numeric: tabular-nums')
  })
})
