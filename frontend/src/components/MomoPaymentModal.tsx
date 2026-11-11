import { useState, useEffect } from 'react'
import { paymentsApi } from '../api/payments'

interface Props {
  rentRecordId?: string
  listingId?: string
  amount: number
  onSuccess: () => void
  onClose: () => void
}

export default function MomoPaymentModal({ rentRecordId, listingId, amount, onSuccess, onClose }: Props) {
  const [step, setStep] = useState<'input' | 'waiting' | 'failed' | 'success'>('input')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [reference, setReference] = useState<string | null>(null)

  useEffect(() => {
    let interval: any;
    if (step === 'waiting' && reference) {
      interval = setInterval(async () => {
        try {
          const res = await paymentsApi.checkStatus(reference)
          if (res.status === 'SUCCESS') {
            setStep('success')
            setTimeout(onSuccess, 1500)
          } else if (res.status === 'FAILED') {
            setStep('failed')
            setError('Payment failed or was cancelled on your phone.')
          }
        } catch (e) { /* ignore network error */ }
      }, 5000)
    }
    return () => clearInterval(interval)
  }, [step, reference, onSuccess])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setStep('waiting')
    try {
      const res = await paymentsApi.initiatePayment({
        rent_record_id: rentRecordId,
        listing_id: listingId,
        amount,
        phone_number: phone
      })
      setReference(res.reference)
    } catch (err: any) {
      setError(err.message)
      setStep('failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold mb-4">Pay with MTN MoMo</h2>
        
        {step === 'input' && (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-gray-600">A prompt will be sent to your phone to enter your PIN.</p>
            <div>
              <label className="block text-sm font-medium mb-1">MTN Phone Number</label>
              <input required value={phone} onChange={e => setPhone(e.target.value)} placeholder="e.g. 260966456787" className="w-full border rounded px-3 py-2" />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={onClose} className="flex-1 bg-gray-100 py-2 rounded">Cancel</button>
              <button type="submit" className="flex-1 bg-emerald-600 text-white py-2 rounded font-medium">Pay K{amount}</button>
            </div>
          </form>
        )}

        {step === 'waiting' && (
          <div className="text-center py-8">
            <div className="w-12 h-12 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="font-bold">Waiting for approval...</p>
            <p className="text-sm text-gray-500 mt-2">Please check your phone and enter your MoMo PIN.</p>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center py-8 text-green-600">
            <h3 className="font-bold text-xl">Payment Successful!</h3>
          </div>
        )}

        {step === 'failed' && (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <button onClick={() => setStep('input')} className="bg-gray-800 text-white px-6 py-2 rounded">Try Again</button>
          </div>
        )}
      </div>
    </div>
  )
}
