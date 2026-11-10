import { api } from './client'

export const managementApi = {
  listLeases: () => api<{results: any[]}>('/leases/'),
  createLease: (data: any) => api('/leases/', { method: 'POST', body: JSON.stringify(data) }),
  markRentPaid: (leaseId: string, recordId: string) => api(`/leases/${leaseId}/rent-records/${recordId}/mark_paid/`, { method: 'POST' })
}

export const leaseApi = {
  get: (id: string) => api<any>(`/leases/${id}/`),
  generateAgreement: (id: string) => api<any>(`/leases/${id}/generate_agreement/`, { method: 'POST' }),
  sign: (id: string) => api<any>(`/leases/${id}/sign/`, { method: 'POST' }),
}
