import { api } from './client'

export const managementApi = {
  listLeases: () => api<{results: any[]}>('/leases/'),
  createLease: (data: any) => api('/leases/', { method: 'POST', body: JSON.stringify(data) }),
  markRentPaid: (leaseId: string, recordId: string) => api(`/leases/${leaseId}/rent-records/${recordId}/mark_paid/`, { method: 'POST' })
}
