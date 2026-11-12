import { api } from './client'

export const paymentsApi = {
  getWallet: () => api<{ balance: number }>('/wallet/'),
  buyCredits: (amount: number, phone: string) =>
    api<{ reference: string }>('/wallet/buy/', {
      method: 'POST',
      body: JSON.stringify({ amount, phone_number: phone })
    }),
  mockWebhook: (reference: string) =>
    api('/wallet/mock_webhook/', {
      method: 'POST',
      body: JSON.stringify({ reference, success: true })
    }),
  unlockListing: (listingId: string) =>
    api('/unlock/unlock/', {
      method: 'POST',
      body: JSON.stringify({ listing_id: listingId })
    }),
  checkStatus: (reference: string) =>
    api<{ status: string }>(`/payments/status/${reference}/`),
}