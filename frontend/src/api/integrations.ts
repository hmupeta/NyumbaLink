
import { api } from './client'

export const integrationsApi = {
  getSettings: () => api<any>('/payment-settings/'),
  updateSettings: (data: any) => api('/payment-settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  connectStripe: (refreshUrl: string, returnUrl: string) => 
    api<{ url: string }>('/payment-settings/stripe_connect/', {
      method: 'POST',
      body: JSON.stringify({ refresh_url: refreshUrl, return_url: returnUrl })
    }),
  initiatePayment: (data: any) => api<any>('/payment-settings/initiate_payment/', {
  checkStatus: async (reference: string) => {
    // TODO: replace with real backend endpoint if needed
    const res = await fetch(`/api/v1/payments/status/${reference}/`);
    return res.json();
  },
    method: 'POST',
    body: JSON.stringify(data)
  })
}
