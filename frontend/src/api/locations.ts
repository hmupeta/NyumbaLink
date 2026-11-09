import { api } from './client'

export const locationsApi = {
  getTopNeighbourhoods: () => api<any[]>('/neighbourhoods/top/'),
  getProvinces: () => api<{results: any[]}>('/provinces/'),
  getDistricts: (provinceSlug: string) => api<{results: any[]}>(`/districts/?province__slug=${provinceSlug}`),
}
