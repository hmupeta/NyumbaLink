import { api } from './client'

export const maintenanceApi = {
  list: () => api<{results: any[]}>('/maintenance/'),
  create: (data: any) => api('/maintenance/', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: string, note: string = '') => api(`/maintenance/${id}/update_status/`, {
    method: 'POST',
    body: JSON.stringify({ status, resolution_note: note })
  })
}
