import { api } from './client'

export const heroApi = {
  list: () => api<{results: any[]}>('/hero-images/'),
}
