import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'

export default function RecommendationsSection() {
  const { user } = useAuth()
  const { data: recs } = useQuery({
    queryKey: ['recommendations'],
    queryFn: listingsApi.getRecommendations,
    enabled: !!user,
  })

  return (
    <div className="bg-[#F8F9FA] py-16 border-b">
      <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-12">
        
        {/* Left Side: Text & CTA */}
        <div className="w-full md:w-1/2">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Get home recommendations</h2>
          <p className="text-lg text-gray-600 mb-6">
            {user 
              ? "Handpicked properties based on your activity on NyumbaLink."
              : "Sign in for a more personalized experience based on your budget and preferred locations."}
          </p>
          {!user && (
            <Link 
              to="/login" 
              className="inline-block border-2 border-[#006AFF] text-[#006AFF] font-semibold px-6 py-2.5 rounded-md hover:bg-blue-50 transition"
            >
              Sign in
            </Link>
          )}
        </div>

        {/* Right Side: Stacked Cards UI */}
        <div className="w-full md:w-1/2 relative h-[320px] flex justify-center">
          {!user ? (
             // Anonymous state (Zillow style mockup)
            <div className="relative w-72 h-full">
              <div className="absolute top-10 left-8 w-full h-[220px] bg-white rounded-xl shadow-lg border p-3 opacity-60 transform scale-90 rotate-6">
                 <div className="w-full h-32 bg-gray-200 rounded-lg mb-2"></div>
                 <div className="h-4 bg-gray-200 w-3/4 rounded"></div>
              </div>
              <div className="absolute top-5 left-4 w-full h-[240px] bg-white rounded-xl shadow-xl border p-3 opacity-80 transform scale-95 rotate-3">
                 <div className="w-full h-36 bg-gray-200 rounded-lg mb-2"></div>
                 <div className="h-4 bg-gray-200 w-3/4 rounded"></div>
              </div>
              <div className="absolute top-0 left-0 w-full h-[260px] bg-white rounded-xl shadow-2xl border p-3 z-10 flex flex-col">
                 <div className="w-full h-40 bg-gray-100 rounded-lg mb-3 flex items-center justify-center text-gray-400">Image</div>
                 <h3 className="font-bold text-lg">K 695,000</h3>
                 <p className="text-sm text-gray-600">4 bd | 3 ba | 3,102 sqft</p>
                 
                 <div className="absolute -left-12 top-4 bg-white rounded-full shadow-lg px-4 py-2 flex items-center gap-2">
                   <div className="bg-emerald-100 p-1.5 rounded-full text-emerald-600">
                     <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
                   </div>
                   <div>
                     <p className="text-xs font-bold m-0">Recommended homes</p>
                     <p className="text-[10px] text-gray-500 m-0">based on your monthly budget</p>
                   </div>
                 </div>
              </div>
            </div>
          ) : (
            // Logged in state (Real Data)
            <div className="grid grid-cols-2 gap-4 w-full">
              {recs?.slice(0, 2).map((listing: any, i: number) => (
                <Link key={listing.id} to={`/listings/${listing.id}`} className={`bg-white rounded-xl shadow border overflow-hidden block ${i === 1 ? 'translate-y-8' : ''}`}>
                  <div className="h-32 bg-gray-100">
                    {listing.media[0] && <img src={getMediaUrl(listing.media[0].file)} className="w-full h-full object-cover" />}
                  </div>
                  <div className="p-3">
                    <h3 className="font-bold text-sm truncate">{listing.title}</h3>
                    <p className="text-emerald-700 font-bold mt-1 text-sm">{listing.currency} {Number(listing.price).toLocaleString()}</p>
                  </div>
                </Link>
              ))}
              {recs?.length === 0 && <div className="col-span-2 text-center text-gray-500 py-10">No recommendations yet. Save some properties!</div>}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
