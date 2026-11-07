import { api } from './client'

export const locationsApi = {
  getProvinces: () => api<{results: any[]}>('/provinces/'),
  getDistricts: (provinceSlug: string) => api<{results: any[]}>(`/districts/?province__slug=${provinceSlug}`),
}
