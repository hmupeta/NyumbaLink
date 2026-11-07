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

export async function api<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const isFormData = options.body instanceof FormData
  
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  })

  // Handle expired access tokens by refreshing them automatically
  if (res.status === 401 && !isRetry && !path.includes('/auth/')) {
    try {
      const refreshRes = await fetch(`${API_URL}/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
      })
      if (refreshRes.ok) {
        return api<T>(path, options, true)
      }
    } catch {
      // Refresh failed, fall through to error
    }
  }

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export { API_URL }
