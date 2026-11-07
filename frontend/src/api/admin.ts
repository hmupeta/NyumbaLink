import { api } from './client'

export const adminApi = {
  getStats: () => api<any>('/auth/admin-stats/'),
}
