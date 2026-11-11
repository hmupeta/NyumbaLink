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
  requestPasswordReset: (email: string, origin: string) => api('/auth/password-reset/', {
    method: 'POST',
    body: JSON.stringify({ email, origin }),
  }),
  resetPassword: (uid: string, token: string, password: string) => api('/auth/password-reset/confirm/', {
    method: 'POST',
    body: JSON.stringify({ uid, token, password }),
  }),
}
