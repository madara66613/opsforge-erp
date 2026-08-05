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
    throw await responseError(response)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function uploadCsv<T>(path: string, token: string, file: File): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      'Content-Type': 'text/csv',
    },
    body: await file.text(),
  })
  if (!response.ok) throw await responseError(response)
  return response.json() as Promise<T>
}

export async function downloadCsv(path: string, token: string, filename: string): Promise<void> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { Accept: 'text/csv', Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw await responseError(response)
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

async function responseError(response: Response): Promise<ApiError> {
  const payload = (await response.json().catch(() => null)) as {
    detail?: string | { message?: string; errors?: Array<{ row: number; field: string; message: string }> }
  } | null
  const detail = payload?.detail
  if (typeof detail === 'string') return new ApiError(detail, response.status)
  if (detail?.message) {
    const first = detail.errors?.[0]
    const context = first ? ` Row ${first.row}, ${first.field}: ${first.message}` : ''
    return new ApiError(`${detail.message}.${context}`, response.status)
  }
  return new ApiError(`Request failed with status ${response.status}`, response.status)
}

export function login(email: string, password: string): Promise<Session> {
  return api<Session>('/auth/login', { method: 'POST', body: { email, password } })
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
