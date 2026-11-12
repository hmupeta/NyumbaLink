import { api } from './client'

export const integrationsApi = {
  getSettings: () => api<any>('/payment-settings/'),

  updateSettings: (data: any) =>
    api('/payment-settings/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  connectStripe: (refreshUrl: string, returnUrl: string) =>
    api<{ url: string }>('/payment-settings/stripe_connect/', {
      method: 'POST',
      body: JSON.stringify({ refresh_url: refreshUrl, return_url: returnUrl }),
    }),

  initiatePayment: (data: any) =>
    api<{ reference: string }>('/payment-settings/initiate_payment/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  checkStatus: (reference: string) =>
    api<{ status: string }>(`/payments/status/${reference}/`),
}