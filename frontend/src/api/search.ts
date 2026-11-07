import { api } from './client'

export const searchApi = {
  list: () => api<{results: any[]}>('/saved-searches/'),
  create: (data: any) => api('/saved-searches/', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: string) => api(`/saved-searches/${id}/`, { method: 'DELETE' }),
}
