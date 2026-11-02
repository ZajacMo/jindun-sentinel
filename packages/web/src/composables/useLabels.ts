/**
 * Label helpers bound to the active locale.
 *
 * Every label the UI shows for a language-neutral code goes through here, so
 * a code such as `"P1"` is turned into the catalogue message `severity.P1` in
 * exactly one place.
 */
import { useI18n } from 'vue-i18n'
import {
  countryLabelKey,
  indicatorLabelKey,
  lensLabelKey,
  marketLabelKey,
  methodLabelKey,
  nodeLabelKey,
  qualityLabelKey,
  regimeLabelKey,
  scopeLabelKey,
  severityLabelKey,
  unitLabelKey,
} from '@/utils/codes'

export function useLabels() {
  const { t, locale } = useI18n()

  return {
    t,
    locale,
    country: (code: string): string => t(countryLabelKey(code)),
    severity: (code: string): string => t(severityLabelKey(code)),
    regime: (code: string): string => t(regimeLabelKey(code)),
    market: (code: string): string => t(marketLabelKey(code)),
    indicator: (code: string, labelKey?: string | null): string =>
      t(indicatorLabelKey(code, labelKey)),
    method: (code: string): string => t(methodLabelKey(code)),
    lens: (code: string): string => t(lensLabelKey(code)),
    scope: (code: string): string => t(scopeLabelKey(code)),
    quality: (code: string): string => t(qualityLabelKey(code)),
    unit: (code: string): string => t(unitLabelKey(code)),
    node: (node: string): string => t(nodeLabelKey(node)),
  }
}
