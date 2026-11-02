/**
 * Formatting helpers bound to the active locale.
 *
 * The locale is read from the preferences store, so every number and date on
 * screen follows the language the analyst selected.
 */
import { computed } from 'vue'
import { usePrefsStore } from '@/stores/prefs'
import {
  formatDate,
  formatDateTime,
  formatDays,
  formatNumber,
  formatPercent,
  formatShare,
} from '@/utils/format'

export function useFormat() {
  const prefs = usePrefsStore()
  const locale = computed(() => prefs.locale)

  return {
    locale,
    number: (value: number | null | undefined, digits = 2): string =>
      formatNumber(value, locale.value, { maximumFractionDigits: digits }),
    percent: (value: number | null | undefined, digits = 1): string =>
      formatPercent(value, locale.value, { maximumFractionDigits: digits }),
    share: (value: number | null | undefined, digits = 2): string =>
      formatShare(value, locale.value, digits),
    date: (
      value: string | number | Date | null | undefined,
      style: 'short' | 'medium' | 'long' = 'medium',
    ): string => formatDate(value, locale.value, style),
    dateTime: (value: string | number | Date | null | undefined): string =>
      formatDateTime(value, locale.value),
    days: (value: number | null | undefined): string => formatDays(value, locale.value),
  }
}
