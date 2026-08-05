import type { Session } from '../types'

const API_ROOT = '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ApiOptions extends Omit<RequestInit, 'body'> {
  token?: string
  body?: unknown
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`)
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(payload?.detail ?? `Request failed with status ${response.status}`, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function login(email: string, password: string): Promise<Session> {
  return api<Session>('/auth/login', { method: 'POST', body: { email, password } })
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
