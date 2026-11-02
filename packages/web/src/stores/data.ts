/**
 * The fetched data of the application.
 *
 * Every endpoint is modelled as a resource with an explicit status, so a page
 * can always tell the difference between "not loaded yet", "loading",
 * "failed" and "loaded but empty" — and can render the failure instead of an
 * empty screen.
 */
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/endpoints'
import { ApiError } from '@/api/client'
import type {
  AlertPayload,
  CountryIndexPayload,
  CountrySummary,
  GsibEntry,
  QualityPayload,
  SpilloverPayload,
} from '@/api/types'

export type ResourceStatus = 'idle' | 'loading' | 'success' | 'error'

export interface Resource<T> {
  status: ResourceStatus
  error: string | null
  data: T | null
}

function emptyResource<T>(): Resource<T> {
  return { status: 'idle', error: null, data: null }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status > 0
      ? `${error.message} (${error.status})`
      : `${error.message} — the API is unreachable`
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

export const useDataStore = defineStore('data', () => {
  const countries = ref<Resource<CountrySummary[]>>(emptyResource())
  const indexByCountry = ref<Record<string, Resource<CountryIndexPayload>>>({})
  const spilloverByCountry = ref<Record<string, Resource<SpilloverPayload>>>({})
  const alertsByCountry = ref<Record<string, Resource<AlertPayload[]>>>({})
  const qualityByCountry = ref<Record<string, Resource<QualityPayload>>>({})
  const globalSpillover = ref<Resource<SpilloverPayload>>(emptyResource())
  const gsib = ref<Resource<GsibEntry[]>>(emptyResource())

  const inFlight = new Map<string, Promise<unknown>>()

  async function loadResource<T>(
    key: string,
    read: () => Resource<T>,
    write: (next: Resource<T>) => void,
    fetcher: () => Promise<T>,
  ): Promise<T | null> {
    if (read().status === 'loading') {
      return read().data
    }
    const existing = inFlight.get(key)
    if (existing) {
      await existing.catch(() => undefined)
      return read().data
    }

    write({ status: 'loading', error: null, data: read().data })
    const promise = fetcher()
      .then((data) => {
        write({ status: 'success', error: null, data })
        return data
      })
      .catch((error: unknown) => {
        write({ status: 'error', error: errorMessage(error), data: null })
        return null
      })
      .finally(() => {
        inFlight.delete(key)
      })

    inFlight.set(key, promise)
    return promise
  }

  function slot<T>(bucket: Record<string, Resource<T>>, key: string): Resource<T> {
    if (!bucket[key]) {
      bucket[key] = emptyResource<T>()
    }
    return bucket[key] as Resource<T>
  }

  function loadCountries(): Promise<CountrySummary[] | null> {
    return loadResource(
      'countries',
      () => countries.value,
      (next) => {
        countries.value = next
      },
      () => api.countries(),
    )
  }

  function loadIndex(code: string, lens = 'percentile'): Promise<CountryIndexPayload | null> {
    return loadResource(
      `index:${code}:${lens}`,
      () => slot(indexByCountry.value, code),
      (next) => {
        indexByCountry.value[code] = next
      },
      () => api.countryIndex(code, lens),
    )
  }

  function loadSpillover(
    code: string,
    method = 'paper_equation',
    horizon = 10,
  ): Promise<SpilloverPayload | null> {
    return loadResource(
      `spillover:${code}:${method}:${horizon}`,
      () => slot(spilloverByCountry.value, code),
      (next) => {
        spilloverByCountry.value[code] = next
      },
      () => api.countrySpillover(code, method, horizon),
    )
  }

  function loadAlerts(code: string): Promise<AlertPayload[] | null> {
    return loadResource(
      `alerts:${code}`,
      () => slot(alertsByCountry.value, code),
      (next) => {
        alertsByCountry.value[code] = next
      },
      () => api.countryAlerts(code),
    )
  }

  function loadQuality(code: string): Promise<QualityPayload | null> {
    return loadResource(
      `quality:${code}`,
      () => slot(qualityByCountry.value, code),
      (next) => {
        qualityByCountry.value[code] = next
      },
      () => api.dataQuality(code),
    )
  }

  function loadGlobalSpillover(
    method = 'paper_equation',
    horizon = 10,
  ): Promise<SpilloverPayload | null> {
    return loadResource(
      `global-spillover:${method}:${horizon}`,
      () => globalSpillover.value,
      (next) => {
        globalSpillover.value = next
      },
      () => api.globalSpillover(method, horizon),
    )
  }

  function loadGsib(): Promise<GsibEntry[] | null> {
    return loadResource(
      'gsib',
      () => gsib.value,
      (next) => {
        gsib.value = next
      },
      () => api.gsib(),
    )
  }

  return {
    countries,
    indexByCountry,
    spilloverByCountry,
    alertsByCountry,
    qualityByCountry,
    globalSpillover,
    gsib,
    loadCountries,
    loadIndex,
    loadSpillover,
    loadAlerts,
    loadQuality,
    loadGlobalSpillover,
    loadGsib,
  }
})
