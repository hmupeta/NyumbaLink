
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { paymentsApi } from '../api/payments'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

export default function WalletPage() {
  const queryClient = useQueryClient()
  const [phone, setPhone] = useState('')
  const [amount, setAmount] = useState(10)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const { data: wallet, isLoading } = useQuery({
    queryKey: ['wallet'],
    queryFn: paymentsApi.getWallet,
  })

  const buyMutation = useMutation({
    mutationFn: () => paymentsApi.buyCredits(amount, phone),
    onSuccess: async (data) => {
      setSuccessMsg('Processing payment... (simulating Mobile Money prompt)')
      setError('')
      
      // Simulate the PSP taking 2 seconds to confirm
      setTimeout(async () => {
        try {
          await paymentsApi.mockWebhook(data.reference)
          queryClient.invalidateQueries({ queryKey: ['wallet'] })
          setSuccessMsg(`Successfully bought ${amount} credits!`)
        } catch {
          setError('Payment failed.')
          setSuccessMsg('')
        }
      }, 2000)
    },
    onError: (err: any) => setError(err.message)
  })

  if (isLoading) return <Loading />

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Your Wallet</h1>
      
      <div className="bg-emerald-600 text-white p-6 rounded-lg mb-8 text-center">
        <p className="text-emerald-100 mb-1">Available Credits</p>
        <p className="text-5xl font-bold">{wallet?.balance || 0}</p>
      </div>

      {error && <ErrorMessage message={error} />}
      {successMsg && (
        <div className="bg-green-50 text-green-700 p-3 rounded mb-4 text-sm">{successMsg}</div>
      )}

      <div className="bg-white border rounded-lg p-6">
        <h2 className="font-bold mb-4">Buy Credits</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Amount</label>
            <select 
              value={amount} onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full border rounded px-3 py-2"
            >
              <option value={10}>10 Credits</option>
              <option value={20}>20 Credits</option>
              <option value={50}>50 Credits</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Mobile Money Number</label>
            <input 
              type="text" placeholder="e.g. 0977123456" 
              value={phone} onChange={(e) => setPhone(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          <button 
            onClick={() => buyMutation.mutate()}
            disabled={buyMutation.isPending || !phone}
            className="w-full bg-gray-900 text-white py-2 rounded hover:bg-black disabled:opacity-50"
          >
            {buyMutation.isPending ? 'Initiating...' : 'Pay with Mobile Money'}
          </button>
        </div>
      </div>
    </div>
  )
}
