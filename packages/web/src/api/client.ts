/**
 * The HTTP layer of the API client.
 *
 * Every request goes through {@link ApiClient.get}, which applies a timeout, a
 * bounded retry with exponential backoff, and turns every failure into an
 * {@link ApiError} carrying the status code and the raw body.  Nothing here
 * swallows an error: the UI renders it.
 */

export const DEFAULT_BASE_URL = 'http://localhost:8000'
export const DEFAULT_TIMEOUT_MS = 10_000
export const DEFAULT_RETRIES = 2

export type QueryValue = string | number | boolean | undefined | null

export interface RequestOptions {
  /** Abort the request after this many milliseconds. */
  timeoutMs?: number
  /** How many *additional* attempts are made after the first one failed. */
  retries?: number
  /** Caller supplied cancellation. */
  signal?: AbortSignal
  /** Query parameters; `undefined` and `null` values are dropped. */
  query?: Record<string, QueryValue>
}

export interface ApiClientOptions {
  baseUrl?: string
  timeoutMs?: number
  retries?: number
  /** Injectable for tests. */
  fetchImpl?: typeof fetch
  /** Injectable for tests; the default waits with `setTimeout`. */
  sleep?: (ms: number) => Promise<void>
}

export class ApiError extends Error {
  readonly status: number
  readonly url: string
  readonly body: string

  constructor(message: string, status: number, url: string, body = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.url = url
    this.body = body
  }

  /** True when the API answered but reported a problem. */
  get isServerError(): boolean {
    return this.status >= 500
  }
}

export function buildQuery(query?: Record<string, QueryValue>): string {
  if (!query) {
    return ''
  }
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue
    }
    params.set(key, String(value))
  }
  const serialised = params.toString()
  return serialised ? `?${serialised}` : ''
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function isRetryableStatus(status: number): boolean {
  return status === 408 || status === 429 || status >= 500
}

export class ApiClient {
  readonly baseUrl: string
  private readonly timeoutMs: number
  private readonly retries: number
  private readonly fetchImpl: typeof fetch
  private readonly sleep: (ms: number) => Promise<void>

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? readBaseUrl()).replace(/\/+$/, '')
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
    this.retries = options.retries ?? DEFAULT_RETRIES
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis)
    this.sleep = options.sleep ?? defaultSleep
  }

  url(path: string, query?: Record<string, QueryValue>): string {
    const suffix = path.startsWith('/') ? path : `/${path}`
    return `${this.baseUrl}${suffix}${buildQuery(query)}`
  }

  async get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.url(path, options.query)
    const timeoutMs = options.timeoutMs ?? this.timeoutMs
    const retries = options.retries ?? this.retries
    let lastError: unknown = null

    for (let attempt = 0; attempt <= retries; attempt += 1) {
      const controller = new AbortController()
      const timer = setTimeout(() => {
        controller.abort()
      }, timeoutMs)
      const onAbort = (): void => controller.abort()
      options.signal?.addEventListener('abort', onAbort)

      try {
        const response = await this.fetchImpl(url, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        })

        if (!response.ok) {
          const body = await safeText(response)
          const error = new ApiError(
            `GET ${url} failed with status ${response.status}`,
            response.status,
            url,
            body,
          )
          if (attempt < retries && isRetryableStatus(response.status)) {
            lastError = error
            await this.sleep(backoffDelay(attempt))
            continue
          }
          throw error
        }

        return (await response.json()) as T
      } catch (error) {
        if (error instanceof ApiError) {
          throw error
        }
        if (options.signal?.aborted) {
          throw error
        }
        lastError = error
        if (attempt >= retries) {
          break
        }
        await this.sleep(backoffDelay(attempt))
      } finally {
        clearTimeout(timer)
        options.signal?.removeEventListener('abort', onAbort)
      }
    }

    const message =
      lastError instanceof Error ? lastError.message : `GET ${url} failed`
    throw new ApiError(message, 0, url)
  }
}

function backoffDelay(attempt: number): number {
  return Math.min(300 * 2 ** attempt, 2_000)
}

async function safeText(response: Response): Promise<string> {
  try {
    return await response.text()
  } catch {
    return ''
  }
}

/** The API base URL, overridable through `VITE_API_BASE`. */
export function readBaseUrl(): string {
  const configured = import.meta.env?.VITE_API_BASE
  return typeof configured === 'string' && configured.length > 0
    ? configured
    : DEFAULT_BASE_URL
}

export const apiClient = new ApiClient()
