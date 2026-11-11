import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getMediaUrl } from '../api/listings'

interface Props {
  onFilterUpdate: (maxPrice: number | undefined, type: 'SALE' | 'RENT' | undefined) => void
  listings: any[]
}

export default function AffordabilityCalculator({ onFilterUpdate, listings }: Props) {
  const [mode, setMode] = useState<'SALE' | 'RENT'>('SALE')
  
  const [income, setIncome] = useState(25000)
  const [downPayment, setDownPayment] = useState(100000)
  const [interestRate, setInterestRate] = useState(18)
  const [termYears, setTermYears] = useState(15)
  
  const [maxHomePrice, setMaxHomePrice] = useState(0)
  const maxMonthlyRent = income * 0.30

  useEffect(() => {
    if (mode === 'SALE') {
      // Mortgage Amortization Formula
      const monthlyPayment = income * 0.30
      const monthlyRate = (interestRate / 100) / 12
      const numPayments = termYears * 12

      let loanAmount = 0
      if (monthlyRate > 0) {
        loanAmount = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
      } else {
        loanAmount = monthlyPayment * numPayments
      }

      const price = loanAmount + downPayment
      setMaxHomePrice(Math.round(price))
      onFilterUpdate(Math.round(price), 'SALE')
    } else {
      onFilterUpdate(Math.round(maxMonthlyRent), 'RENT')
    }
  }, [mode, income, downPayment, interestRate, termYears, onFilterUpdate, maxMonthlyRent])

  // Filter listings strictly by the current mode (SALE vs RENT)
  const affordableListings = listings.filter(l => {
    if (mode === 'SALE') {
      return l.transaction_type === 'SALE' && Number(l.price) <= maxHomePrice;
    } else {
      return l.transaction_type === 'RENT' && Number(l.price) <= maxMonthlyRent;
    }
  });

  return (
    <div className="bg-white py-16">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Find homes you can afford</h2>
          <p className="text-gray-600">Answer a few questions. We'll highlight homes you're likely to qualify for.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          
          <div className="bg-white border rounded-2xl p-6 shadow-sm h-fit">
            <div className="flex items-center gap-2 mb-6">
              <span className="text-blue-600 text-xl font-bold">Z</span>
              <h3 className="font-semibold text-gray-800">NyumbaLink Calculator</h3>
            </div>

            {/* Buy / Rent Tabs */}
            <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
              <button 
                onClick={() => setMode('SALE')}
                className={`flex-1 py-2 text-sm font-semibold rounded-md transition ${mode === 'SALE' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-800'}`}
              >
                Buy
              </button>
              <button 
                onClick={() => setMode('RENT')}
                className={`flex-1 py-2 text-sm font-semibold rounded-md transition ${mode === 'RENT' ? 'bg-white shadow text-emerald-600' : 'text-gray-500 hover:text-gray-800'}`}
              >
                Rent
              </button>
            </div>

            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium text-gray-700">Monthly Income (ZMW)</label>
                <input type="number" value={income} onChange={e => setIncome(Number(e.target.value))} className="w-full text-xl font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
              </div>

              {mode === 'SALE' && (
                <>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Down Payment (ZMW)</label>
                    <input type="number" value={downPayment} onChange={e => setDownPayment(Number(e.target.value))} className="w-full text-xl font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700">Interest Rate (%)</label>
                      <input type="number" value={interestRate} onChange={e => setInterestRate(Number(e.target.value))} className="w-full text-lg font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">Term (Years)</label>
                      <input type="number" value={termYears} onChange={e => setTermYears(Number(e.target.value))} className="w-full text-lg font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className={`mt-8 p-4 rounded-xl text-center ${mode === 'SALE' ? 'bg-blue-50' : 'bg-emerald-50'}`}>
              <p className={`text-sm font-medium ${mode === 'SALE' ? 'text-blue-800' : 'text-emerald-800'}`}>
                {mode === 'SALE' ? 'Max Home Price' : 'Max Monthly Rent'}
              </p>
              <p className={`text-2xl font-bold ${mode === 'SALE' ? 'text-blue-900' : 'text-emerald-900'}`}>
                K {(mode === 'SALE' ? maxHomePrice : maxMonthlyRent).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="md:col-span-2 relative overflow-hidden">
             <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
                {affordableListings.map(l => (
                  <Link key={l.id} to={`/listings/${l.id}`} className="min-w-[280px] w-[280px] snap-start border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition block relative">
                    <div className={`absolute top-0 left-0 text-white text-xs font-bold px-3 py-1 rounded-br-lg z-10 ${mode === 'SALE' ? 'bg-blue-600' : 'bg-emerald-600'}`}>
                      Within Budget
                    </div>
                    <div className="h-40 bg-gray-100">
                      {l.media[0] && <img src={getMediaUrl(l.media[0].file)} className="w-full h-full object-cover" />}
                    </div>
                    <div className="p-4">
                      <h4 className="font-bold text-gray-900 truncate">{l.title}</h4>
                      <p className="text-sm text-gray-500">{l.property_summary.neighbourhood}</p>
                      <p className="font-bold mt-2 text-emerald-700">
                        K {Number(l.price).toLocaleString()} {mode === 'RENT' ? '/mo' : ''}
                      </p>
                    </div>
                  </Link>
                ))}
                {affordableListings.length === 0 && (
                  <p className="text-gray-500 pt-10">
                    No {mode === 'SALE' ? 'properties for sale' : 'rentals'} found within this budget right now.
                  </p>
                )}
             </div>
          </div>

        </div>
      </div>
    </div>
  )
}
