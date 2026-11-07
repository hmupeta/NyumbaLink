import { useState, useEffect } from 'react'
import { Helmet } from 'react-helmet-async'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import { paymentsApi } from '../api/payments'
import { messagingApi } from '../api/messaging'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ImageLightbox from '../components/ImageLightbox'

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [unlockError, setUnlockError] = useState('')
  const [showViewingModal, setShowViewingModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [reportReason, setReportReason] = useState('FRAUD')
  const [reportDesc, setReportDesc] = useState('')
  const [viewingDate, setViewingDate] = useState('')

  useEffect(() => {
    if (id) listingsApi.trackView(id).catch(() => {})
  }, [id])

  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  const unlockMutation = useMutation({
    mutationFn: () => paymentsApi.unlockListing(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['listing', id] })
      setUnlockError('')
    },
    onError: (err: any) => setUnlockError(err.message || 'Not enough credits.')
  })

  const startChatMutation = useMutation({
    mutationFn: () => messagingApi.startConversation(id!),
    onSuccess: (conv) => navigate(`/inbox?c=${conv.id}`)
  })

  const reportMutation = useMutation({
    mutationFn: () => listingsApi.submitReport(id!, reportReason, reportDesc),
    onSuccess: () => {
      setShowReportModal(false)
      alert('Thank you. Your report has been submitted to our moderation team.')
    },
    onError: () => alert('Failed to submit report.')
  })

  const viewingMutation = useMutation({
    mutationFn: () => messagingApi.requestViewing({ listing: id, requested_date: viewingDate, note: "Requested via listing page" }),
    onSuccess: () => {
      setShowViewingModal(false)
      alert('Viewing request sent!')
    }
  })

  if (isLoading) return <Loading />
  if (error || !listing) return <div className="p-8"><ErrorMessage message="Listing not found." /></div>

  const images = listing.media.filter((m) => m.media_type === 'IMAGE')
  const isOwner = user?.id === listing.created_by
  const isUnlocked = false 

  const landlordPhone = "+260970000000" 
  const whatsappMessage = encodeURIComponent(`Hi, I am interested in your property "${listing.title}" on NyumbaLink.`)
  const whatsappLink = `https://wa.me/${landlordPhone.replace(/\D/g, '')}?text=${whatsappMessage}`

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Helmet>
        <title>{listing.title} | NyumbaLink</title>
        <meta name="description" content={`${listing.property_summary.property_type} in ${listing.property_summary.neighbourhood}. ${listing.description?.slice(0, 150)}`} />
        
        {/* Open Graph tags for WhatsApp/Facebook */}
        <meta property="og:title" content={`${listing.title} | NyumbaLink`} />
        <meta property="og:description" content={`${listing.currency} ${Number(listing.price).toLocaleString()} · ${listing.property_summary.neighbourhood}`} />
        <meta property="og:type" content="website" />
        {images.length > 0 && <meta property="og:image" content={getMediaUrl(images[0].file)} />}
        <meta property="og:url" content={window.location.href} />
        
        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>
      <Link to="/" className="text-sm text-emerald-700 hover:underline">← Back to listings</Link>
      <h1 className="text-3xl font-bold mt-4 mb-2">{listing.title}</h1>
      <p className="text-gray-600 mb-6">{listing.property_summary.neighbourhood} · {listing.property_summary.property_type}</p>

      {/* Images */}
      {images.length > 0 && images[0].file ? (
        <div className="grid gap-2 mb-6" style={{ gridTemplateColumns: images.length > 1 ? '2fr 1fr' : '1fr' }}>
          {images.slice(0, 2).map((m, idx) => (
            <div key={m.id} className="relative cursor-pointer group overflow-hidden rounded-lg bg-gray-100" onClick={() => setLightboxIndex(idx)}>
              <img 
                src={getMediaUrl(m.file)} 
                className="w-full h-64 md:h-80 object-cover group-hover:opacity-90 transition" 
                onError={(e) => { (e.target as HTMLImageElement).src = 'https://placehold.co/800x600/e2e8f0/64748b?text=Image+Not+Found'; }}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="w-full h-64 md:h-80 bg-gray-100 rounded-lg mb-6 flex items-center justify-center text-gray-400">
          No images provided for this property
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-semibold text-lg mb-2">Description</h2>
          <p className="whitespace-pre-line text-gray-700">{listing.description || 'No description provided.'}</p>
        </div>
        
        <aside className="border rounded-lg p-4 h-fit bg-white shadow-sm flex flex-col">
          <p className="text-2xl font-bold text-emerald-700">
            {listing.currency} {Number(listing.price).toLocaleString()}
            {listing.price_period === 'MONTH' && <span className="text-base text-gray-500">/mo</span>}
          </p>
          <p className="text-sm text-gray-600 mt-1 mb-4">
            {listing.transaction_type === 'RENT' ? 'For rent' : 'For sale'}
          </p>

          {!user ? (
            <Link to="/login" className="block text-center w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium">
              Log in to contact
            </Link>
          ) : isOwner ? (
            <div className="bg-gray-50 text-center p-3 rounded border text-sm text-gray-600">
              You are the advertiser.
            </div>
          ) : (
            <div className="space-y-3">
              {unlockError && <p className="text-xs text-red-600">{unlockError}</p>}
              
              <button 
                onClick={() => startChatMutation.mutate()}
                disabled={startChatMutation.isPending}
                className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium disabled:opacity-50"
              >
                Message on NyumbaLink
              </button>

              <a 
                href={whatsappLink}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-center gap-2 bg-[#25D366] text-white py-2 rounded hover:bg-[#128C7E] font-medium transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
                WhatsApp Landlord
              </a>

              <button 
                onClick={() => setShowViewingModal(true)}
                className="w-full bg-white border-2 border-emerald-600 text-emerald-700 py-2 rounded hover:bg-emerald-50 font-medium"
              >
                Request Viewing
              </button>

              <div className="text-center pt-2">
                <button onClick={() => unlockMutation.mutate()} className="text-xs text-gray-500 hover:text-emerald-600 underline">
                  {isUnlocked ? 'Contact Unlocked' : 'Unlock Phone Number (5 Credits)'}
                </button>
              </div>
            </div>
          )}

          {/* THE ADVERTISED BY LINK */}
          <div className="mt-6 pt-4 border-t text-center">
             <p className="text-xs text-gray-500 mb-1">Advertised by</p>
             <Link to={`/profiles/${listing.created_by}`} className="text-sm font-bold text-emerald-700 hover:underline">
                View Landlord Profile
             </Link>
             {user && user.id !== listing.created_by && (
               <button onClick={() => setShowReportModal(true)} className="block mx-auto mt-4 text-xs text-red-500 hover:underline">
                 Report this Listing
               </button>
             )}
          </div>
        </aside>
      </div>

      {lightboxIndex !== null && <ImageLightbox images={images} initialIndex={lightboxIndex} onClose={() => setLightboxIndex(null)} />}

      {showReportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-96">
            <h2 className="text-lg font-bold mb-4 text-red-600">Report Listing</h2>
            <p className="text-sm text-gray-600 mb-4">Help us keep NyumbaLink safe. Why are you reporting this?</p>
            
            <select value={reportReason} onChange={e => setReportReason(e.target.value)} className="w-full border rounded px-3 py-2 mb-3 text-sm">
              <option value="FRAUD">Fraud or Scam</option>
              <option value="DUPLICATE">Duplicate Listing</option>
              <option value="WRONG_INFO">Inaccurate Information</option>
              <option value="UNAVAILABLE">Property No Longer Available</option>
              <option value="OFFENSIVE">Offensive Content</option>
            </select>

            <textarea 
              value={reportDesc} onChange={e => setReportDesc(e.target.value)}
              placeholder="Additional details (optional)..." 
              className="w-full border rounded px-3 py-2 mb-4 text-sm" rows={3}
            />

            <div className="flex gap-2">
              <button onClick={() => setShowReportModal(false)} className="flex-1 bg-gray-100 py-2 rounded hover:bg-gray-200">Cancel</button>
              <button 
                onClick={() => reportMutation.mutate()} 
                disabled={reportMutation.isPending}
                className="flex-1 bg-red-600 text-white py-2 rounded hover:bg-red-700 disabled:opacity-50"
              >
                {reportMutation.isPending ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showViewingModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl w-96">
            <h2 className="text-lg font-bold mb-4">Request a Viewing</h2>
            <label className="block text-sm font-medium mb-1">Preferred Date & Time</label>
            <input 
              type="datetime-local" 
              value={viewingDate} 
              onChange={e => setViewingDate(e.target.value)}
              className="w-full border rounded px-3 py-2 mb-4" 
            />
            <div className="flex gap-2">
              <button onClick={() => setShowViewingModal(false)} className="flex-1 bg-gray-100 py-2 rounded hover:bg-gray-200">Cancel</button>
              <button 
                onClick={() => viewingMutation.mutate()} 
                disabled={!viewingDate || viewingMutation.isPending}
                className="flex-1 bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50"
              >
                {viewingMutation.isPending ? 'Sending...' : 'Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
