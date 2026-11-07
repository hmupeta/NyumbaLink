
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { integrationsApi } from '../api/integrations'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

type Provider = 'MTN' | 'AIRTEL' | 'ZAMTEL' | 'STRIPE' | 'PAYPAL'

export default function PaymentSettingsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Provider>('STRIPE')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const { data: settings, isLoading } = useQuery({
    queryKey: ['payment-settings'],
    queryFn: integrationsApi.getSettings,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => integrationsApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payment-settings'] })
      setSuccess('Settings saved.')
      setError('')
    },
    onError: (err: any) => setError(err.message || 'Failed to save.')
  })

  const stripeMutation = useMutation({
    mutationFn: () => integrationsApi.connectStripe(
      window.location.origin + '/settings',
      window.location.origin + '/settings'
    ),
    onSuccess: (data) => { window.location.href = data.url },
    onError: (err: any) => setError(err.message || 'Stripe connection failed.')
  })

  if (isLoading) return <Loading />

  const handleSave = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    const fd = new FormData(e.currentTarget)
    const payload: Record<string, string> = {}
    fd.forEach((v, k) => { if (v) payload[k] = v.toString() })
    updateMutation.mutate(payload)
  }

  const TABS: { key: Provider; label: string }[] = [
    { key: 'STRIPE', label: 'Stripe (Cards)' },
    { key: 'PAYPAL', label: 'PayPal' },
    { key: 'MTN', label: 'MTN MoMo' },
    { key: 'AIRTEL', label: 'Airtel Money' },
    { key: 'ZAMTEL', label: 'Zamtel Kwacha' },
  ]

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Payment Integrations</h1>
      <p className="text-gray-600 mb-6">Connect your own merchant accounts to receive rent directly.</p>

      {error && <ErrorMessage message={error} />}
      {success && <div className="bg-green-50 text-green-700 p-3 rounded mb-4 text-sm">{success}</div>}

      <div className="flex gap-2 mb-6 flex-wrap">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 rounded text-sm font-medium transition ${
              activeTab === t.key ? 'bg-emerald-600 text-white' : 'bg-white border text-gray-700 hover:bg-gray-50'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'STRIPE' && (
        <div className="bg-white border rounded-lg p-6">
          <h2 className="font-bold mb-2">Stripe Connect (Express)</h2>
          <p className="text-sm text-gray-600 mb-4">
            Stripe handles KYC and pays out directly to your bank. Click below to connect.
          </p>
          {settings?.stripe_connected_account_id ? (
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded">
              <p className="text-sm text-emerald-800">
                Connected account: <strong>{settings.stripe_connected_account_id}</strong>
              </p>
              <button onClick={() => stripeMutation.mutate()} className="mt-3 text-sm text-emerald-700 underline">
                Re-run onboarding if needed
              </button>
            </div>
          ) : (
            <button
              onClick={() => stripeMutation.mutate()}
              disabled={stripeMutation.isPending}
              className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 disabled:opacity-50"
            >
              {stripeMutation.isPending ? 'Connecting...' : 'Connect Stripe Account'}
            </button>
          )}
        </div>
      )}

      {activeTab === 'PAYPAL' && (
        <form onSubmit={handleSave} className="bg-white border rounded-lg p-6 space-y-4">
          <h2 className="font-bold">PayPal Commerce</h2>
          <p className="text-sm text-gray-600">Enter your PayPal REST API credentials.</p>
          <div>
            <label className="block text-sm font-medium mb-1">Client ID</label>
            <input name="paypal_client_id" defaultValue={settings?.paypal_client_id || ''} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Client Secret</label>
            <input name="paypal_client_secret" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <button type="submit" disabled={updateMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded">Save PayPal Settings</button>
        </form>
      )}

      {activeTab === 'MTN' && (
        <form onSubmit={handleSave} className="bg-white border rounded-lg p-6 space-y-4">
          <h2 className="font-bold">MTN MoMo Zambia</h2>
          <p className="text-sm text-gray-600">Enter your MTN MoMo API credentials from the MTN Developer Portal.</p>
          <div>
            <label className="block text-sm font-medium mb-1">API User</label>
            <input name="mtn_api_user" defaultValue={settings?.mtn_api_user || ''} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <input name="mtn_api_key" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subscription Key</label>
            <input name="mtn_subscription_key" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Environment</label>
            <select name="mtn_target_environment" defaultValue={settings?.mtn_target_environment || 'mtnzambia'} className="w-full border rounded px-3 py-2">
              <option value="sandbox">Sandbox (EUR)</option>
              <option value="mtnzambia">Production (ZMW)</option>
            </select>
          </div>
          <button type="submit" disabled={updateMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded">Save MTN Settings</button>
        </form>
      )}

      {activeTab === 'AIRTEL' && (
        <form onSubmit={handleSave} className="bg-white border rounded-lg p-6 space-y-4">
          <h2 className="font-bold">Airtel Money Zambia</h2>
          <p className="text-sm text-gray-600">OAuth 2.0 credentials from developers.airtel.africa.</p>
          <div>
            <label className="block text-sm font-medium mb-1">Client ID</label>
            <input name="airtel_client_id" defaultValue={settings?.airtel_client_id || ''} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Client Secret</label>
            <input name="airtel_client_secret" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <button type="submit" disabled={updateMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded">Save Airtel Settings</button>
        </form>
      )}

      {activeTab === 'ZAMTEL' && (
        <form onSubmit={handleSave} className="bg-white border rounded-lg p-6 space-y-4">
          <h2 className="font-bold">Zamtel Kwacha</h2>
          <p className="text-sm text-gray-600">Configure your Zamtel merchant endpoint or aggregator URL.</p>
          <div>
            <label className="block text-sm font-medium mb-1">Merchant ID</label>
            <input name="zamtel_merchant_id" defaultValue={settings?.zamtel_merchant_id || ''} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <input name="zamtel_api_key" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">API Base URL</label>
            <input name="zamtel_api_base_url" defaultValue={settings?.zamtel_api_base_url || 'https://api.zamtel.com/kwacha'} className="w-full border rounded px-3 py-2" />
          </div>
          <button type="submit" disabled={updateMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded">Save Zamtel Settings</button>
        </form>
      )}
    </div>
  )
}
