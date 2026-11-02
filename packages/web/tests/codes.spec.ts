import { describe, expect, it } from 'vitest'
import {
  countryLabelKey,
  indicatorLabelKey,
  isRegimeCode,
  isSeverityCode,
  marketLabelKey,
  methodLabelKey,
  nodeLabelKey,
  regimeLabelKey,
  severityLabelKey,
} from '@/utils/codes'

/**
 * The API hands out language-neutral codes; the front end has to turn them
 * into the message keys of the shared catalogue.  These tests pin that
 * mapping, because a wrong key silently renders the raw code.
 */
describe('locale mapping helpers', () => {
  it('maps a country code to its catalogue key', () => {
    expect(countryLabelKey('CN')).toBe('country.CN')
    expect(countryLabelKey('US')).toBe('country.US')
    expect(countryLabelKey('EU')).toBe('country.EU')
    expect(countryLabelKey('GB')).toBe('country.GB')
    expect(countryLabelKey('JP')).toBe('country.JP')
  })

  it('maps a severity code to its catalogue key', () => {
    expect(severityLabelKey('P1')).toBe('severity.P1')
    expect(severityLabelKey('P2')).toBe('severity.P2')
    expect(severityLabelKey('P3')).toBe('severity.P3')
  })

  it('maps the remaining enumerations to their catalogue keys', () => {
    expect(regimeLabelKey('moderate')).toBe('regime.moderate')
    expect(regimeLabelKey('high')).toBe('regime.high')
    expect(marketLabelKey('equity')).toBe('market.equity')
    expect(methodLabelKey('paper_equation')).toBe('method.paper_equation')
    expect(indicatorLabelKey('pe_ratio')).toBe('indicator.pe_ratio')
  })

  it('prefers an explicit label key over the generated one', () => {
    expect(indicatorLabelKey('pe_ratio', 'indicator.custom')).toBe('indicator.custom')
    expect(indicatorLabelKey('pe_ratio', null)).toBe('indicator.pe_ratio')
    expect(indicatorLabelKey('pe_ratio', '')).toBe('indicator.pe_ratio')
  })

  it('resolves a network node through the matching namespace', () => {
    expect(nodeLabelKey('equity')).toBe('market.equity')
    expect(nodeLabelKey('CN')).toBe('country.CN')
    expect(nodeLabelKey('unknown-node')).toBe('unknown-node')
  })

  it('recognises the known severity and regime codes', () => {
    expect(isSeverityCode('P1')).toBe(true)
    expect(isSeverityCode('P9')).toBe(false)
    expect(isSeverityCode(42)).toBe(false)
    expect(isRegimeCode('high')).toBe(true)
    expect(isRegimeCode('extreme')).toBe(false)
  })
})
