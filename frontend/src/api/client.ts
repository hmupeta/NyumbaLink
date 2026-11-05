const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number
  data: unknown
  constructor(status: number, data: unknown) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String((data as Record<string, unknown>).detail)
        : `HTTP ${status}`
    super(detail)
    this.status = status
    this.data = data
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export { API_URL }
