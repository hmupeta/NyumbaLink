import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getMediaUrl } from '../api/listings'

interface Props {
  onBudgetChange: (maxPrice: number | undefined) => void
  listings: any[]
}

export default function AffordabilityCalculator({ onBudgetChange, listings }: Props) {
  const [income, setIncome] = useState(25000) // ZMW
  const [downPayment, setDownPayment] = useState(100000) // ZMW
  const [interestRate, setInterestRate] = useState(18) // Typical Zambian mortgage rate
  const [termYears, setTermYears] = useState(15)

  // Calculate maximum affordable price
  useEffect(() => {
    // 1. Calculate the monthly housing budget (30% of income)
    const monthlyPayment = income * 0.30
    
    // 2. Calculate the loan amount using standard mortgage amortization
    const monthlyRate = (interestRate / 100) / 12
    const numPayments = termYears * 12
    
    let loanAmount = 0
    if (monthlyRate > 0) {
      // Standard Mortgage Formula: P = M * [(1+r)^n - 1] / [r * (1+r)^n]
      loanAmount = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
    } else {
      // If interest is 0%, simple multiplication
      loanAmount = monthlyPayment * numPayments
    }

    // 3. Add down payment to get the max home price
    const maxHomePrice = loanAmount + downPayment
    onBudgetChange(Math.round(maxHomePrice))
  }, [income, downPayment, interestRate, termYears, onBudgetChange])

  // Filter listings that fall within the calculated budget
  // (We compute the max price exactly as we did in the useEffect above)
  const monthlyPayment = income * 0.30
  const monthlyRate = (interestRate / 100) / 12
  const numPayments = termYears * 12
  let maxLoan = 0
  if (monthlyRate > 0) {
    maxLoan = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
  } else {
    maxLoan = monthlyPayment * numPayments
  }
  const maxAffordablePrice = maxLoan + downPayment

  const affordableListings = listings.filter(l => Number(l.price) <= maxAffordablePrice)

  return (
    <div className="bg-white py-16">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Find homes you can afford</h2>
          <p className="text-gray-600">Answer a few questions. We'll highlight homes you're likely to qualify for.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          
          {/* Calculator Panel */}
          <div className="bg-white border rounded-2xl p-6 shadow-sm h-fit">
            <div className="flex items-center gap-2 mb-6">
              <span className="text-blue-600 text-xl font-bold">Z</span>
              <h3 className="font-semibold text-gray-800">NyumbaLink Calculator</h3>
            </div>

            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium text-gray-700">Monthly Income (ZMW)</label>
                <input type="number" value={income} onChange={e => setIncome(Number(e.target.value))} className="w-full text-xl font-bold border-b-2 border-gray-300 py-1 focus:outline-none focus:border-blue-600 bg-transparent" />
              </div>

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
            </div>

            <div className="mt-8 bg-blue-50 p-4 rounded-xl text-center">
              <p className="text-sm text-blue-800 font-medium">Max Home Price</p>
              <p className="text-2xl font-bold text-blue-900">
                K {Math.round(income * 0.30 * termYears * 12 + downPayment).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Listings Carousel */}
          <div className="md:col-span-2 relative overflow-hidden">
             <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
                {affordableListings.map(l => (
                  <Link key={l.id} to={`/listings/${l.id}`} className="min-w-[280px] w-[280px] snap-start border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition block relative">
                    <div className="absolute top-0 left-0 bg-orange-500 text-white text-xs font-bold px-3 py-1 rounded-br-lg z-10">Within Budget</div>
                    <div className="h-40 bg-gray-100">
                      {l.media[0] && <img src={getMediaUrl(l.media[0].file)} className="w-full h-full object-cover" />}
                    </div>
                    <div className="p-4">
                      <h4 className="font-bold text-gray-900 truncate">{l.title}</h4>
                      <p className="text-sm text-gray-500">{l.property_summary.neighbourhood}</p>
                      <p className="font-bold text-emerald-700 mt-2">K {Number(l.price).toLocaleString()}</p>
                    </div>
                  </Link>
                ))}
                {affordableListings.length === 0 && <p className="text-gray-500 pt-10">No listings within this budget right now.</p>}
             </div>
          </div>

        </div>
      </div>
    </div>
  )
}
