import { api } from './client'
import type { User } from './types'

export const authApi = {
  login: (email: string, password: string) =>
    api<{ user: User }>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, firstName = '', lastName = '') =>
    api<{ user: User }>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        email, password,
        first_name: firstName,
        last_name: lastName,
      }),
    }),

  logout: () => api<void>('/auth/logout/', { method: 'POST' }),
  me: () => api<User>('/auth/me/'),
}
