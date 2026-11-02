/**
 * The typed endpoint functions of the JinDun Sentinel API.
 *
 * Each function returns the *normalised* shape declared in `./types`, so the
 * rest of the application never has to know how the wire format looks.
 */
import { apiClient, ApiError } from './client'
import type { ApiClient } from './client'
import {
  normaliseAlerts,
  normaliseCountries,
  normaliseGsib,
  normaliseIndexPayload,
  normaliseQualityPayload,
  normaliseSpilloverPayload,
} from './types'
import type {
  AlertPayload,
  CountryIndexPayload,
  CountrySummary,
  GsibEntry,
  QualityPayload,
  SpilloverPayload,
} from './types'

export interface HealthPayload {
  status: string
  version: string | null
  generatedAt: string | null
}

/**
 * The reason a resource is absent, when the API reports one.
 *
 * The API distinguishes "this economy has no such network by construction"
 * from "the network could not be computed" — the two must never look the
 * same to the user, so the reason is parsed out of the structured error
 * detail instead of being inferred from the status code.
 */
function unavailableReason(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.status !== 404) {
    return null
  }
  try {
    const parsed = JSON.parse(error.body) as { detail?: { reason?: unknown } }
    const reason = parsed.detail?.reason
    return typeof reason === 'string' ? reason : null
  } catch {
    return null
  }
}

export function createApi(client: ApiClient = apiClient) {
  return {
    async health(): Promise<HealthPayload> {
      const raw = (await client.get('/api/v1/health')) as Record<string, unknown>
      const record = typeof raw === 'object' && raw !== null ? raw : {}
      return {
        status: typeof record.status === 'string' ? record.status : 'unknown',
        version:
          typeof record.version === 'string'
            ? record.version
            : typeof record['version'] === 'string'
              ? (record['version'] as string)
              : null,
        generatedAt:
          typeof record.generated_at === 'string' ? record.generated_at : null,
      }
    },

    async countries(): Promise<CountrySummary[]> {
      return normaliseCountries(await client.get('/api/v1/countries'))
    },

    async countryIndex(
      code: string,
      lens = 'percentile',
    ): Promise<CountryIndexPayload> {
      const raw = await client.get(`/api/v1/countries/${code}/index`, {
        query: { lens },
      })
      return normaliseIndexPayload(raw, code)
    },

    async countrySpillover(
      code: string,
      method = 'paper_equation',
      horizon = 10,
    ): Promise<SpilloverPayload> {
      try {
        const raw = await client.get(`/api/v1/countries/${code}/spillover`, {
          query: { method, horizon },
        })
        return normaliseSpilloverPayload(raw)
      } catch (error) {
        const reason = unavailableReason(error)
        if (!reason) {
          throw error
        }
        // An economy measured by a published official index has no cross-market
        // network.  That is a property of the economy, not a failure, so it is
        // reported as an absent resource rather than as an error.
        return {
          scope: code.toUpperCase(),
          nodes: [],
          matrix: [],
          totalSpillout: {},
          totalSpillin: {},
          net: {},
          horizon,
          method,
          defaultMethod: method,
          availableMethods: [],
          available: false,
          unavailableReason: reason,
          window: null,
          notes: [],
          varOrder: null,
        }
      }
    },

    async countryAlerts(code: string): Promise<AlertPayload[]> {
      return normaliseAlerts(await client.get(`/api/v1/countries/${code}/alerts`))
    },

    async globalSpillover(method = 'paper_equation', horizon = 10): Promise<SpilloverPayload> {
      const raw = await client.get('/api/v1/global/spillover', {
        query: { method, horizon },
      })
      return normaliseSpilloverPayload(raw)
    },

    async gsib(): Promise<GsibEntry[]> {
      return normaliseGsib(await client.get('/api/v1/global/gsib'))
    },

    async dataQuality(code: string): Promise<QualityPayload> {
      try {
        // The API nests the quality report under the country.
        return normaliseQualityPayload(
          await client.get(`/api/v1/countries/${code}/data-quality`),
        )
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          // Fall back to the flat path the endpoint contract documents.
          return normaliseQualityPayload(await client.get(`/api/v1/data-quality/${code}`))
        }
        throw error
      }
    },
  }
}

export type SentinelApi = ReturnType<typeof createApi>

export const api = createApi()
