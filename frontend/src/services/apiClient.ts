import { config } from '../config'
import type { ErrorDetail, ErrorResponse } from '../types/api'

/**
 * The only place the frontend calls fetch(). Components use the typed functions in
 * services/*.ts, never fetch directly.
 */

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ErrorDetail[]
  readonly requestId: string | null

  constructor(status: number, code: string, message: string, details: ErrorDetail[] = [], requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

type Query = Record<string, string | number | boolean | string[] | undefined | null>

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Query
  signal?: AbortSignal
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === 'object' &&
    value !== null &&
    'error' in value &&
    typeof (value as ErrorResponse).error?.code === 'string'
  )
}

export function buildUrl(baseUrl: string, path: string, query?: Query): string {
  const url = new URL(path.replace(/^\/+/, ''), `${baseUrl}/`)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null) continue
    for (const item of Array.isArray(value) ? value : [value]) {
      url.searchParams.append(key, String(item))
    }
  }
  return url.toString()
}

export class ApiClient {
  private readonly baseUrl: string
  private readonly fetchImpl: typeof fetch

  constructor(baseUrl: string = config.apiBaseUrl, fetchImpl?: typeof fetch) {
    this.baseUrl = baseUrl
    this.fetchImpl = fetchImpl ?? ((...args) => globalThis.fetch(...args))
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, query, signal } = options
    let response: Response
    try {
      response = await this.fetchImpl(buildUrl(this.baseUrl, path, query), {
        method,
        signal,
        headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
      throw new ApiError(0, 'network_error', 'Cannot reach the AGENT X server. Check that the backend is running.')
    }

    const text = await response.text()
    let data: unknown = null
    if (text) {
      try {
        data = JSON.parse(text)
      } catch {
        data = null
      }
    }

    if (!response.ok) {
      if (isErrorResponse(data)) {
        const { code, message, details, request_id } = data.error
        throw new ApiError(response.status, code, message, details, request_id)
      }
      throw new ApiError(response.status, 'http_error', `Request failed with status ${response.status}`)
    }
    return data as T
  }

  get<T>(path: string, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  post<T>(path: string, body: unknown, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body })
  }
}

export const apiClient = new ApiClient()
