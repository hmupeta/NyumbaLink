import { Link } from 'react-router-dom'

export default function IntentCards() {
  return (
    <div className="bg-[#F8F9FA] py-16 border-b">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-6">
          
          {/* Card 1: Buy */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-blue-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#006AFF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Buy a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              Find your place with an immersive photo experience and the most listings, including things you won't find anywhere else.
            </p>
            <Link to="/?type=sale" className="mt-auto px-6 py-2.5 border-2 border-[#006AFF] text-[#006AFF] font-semibold rounded-lg hover:bg-blue-50 transition">
              Browse homes
            </Link>
          </div>

          {/* Card 2: Rent */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-emerald-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="3" y1="9" x2="21" y2="9"></line>
                <line x1="9" y1="21" x2="9" y2="9"></line>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Rent a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              We're creating a seamless online experience – from shopping on the largest rental network, to applying, to paying rent.
            </p>
            <Link to="/?type=rent" className="mt-auto px-6 py-2.5 border-2 border-emerald-600 text-emerald-700 font-semibold rounded-lg hover:bg-emerald-50 transition">
              Find rentals
            </Link>
          </div>

          {/* Card 3: Sell/List */}
          <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition flex flex-col items-center text-center">
            <div className="w-32 h-32 mb-6 rounded-full bg-orange-50 flex items-center justify-center">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#EA580C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Sell or List a home</h3>
            <p className="text-gray-600 mb-6 text-sm leading-relaxed">
              No matter what path you take to sell your home, we can help you navigate a successful sale.
            </p>
            <Link to="/dashboard/listings/new" className="mt-auto px-6 py-2.5 border-2 border-orange-500 text-orange-600 font-semibold rounded-lg hover:bg-orange-50 transition">
              List your property
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
