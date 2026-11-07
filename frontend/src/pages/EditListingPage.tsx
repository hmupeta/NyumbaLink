import { useState, type FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

export default function EditListingPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [newFiles, setNewFiles] = useState<File[]>([])

  const { data: listing, isLoading: loadingListing } = useQuery({
    queryKey: ['manage-listing', id],
    queryFn: () => listingsApi.get(id!),
    enabled: !!id,
  })

  const { data: property, isLoading: loadingProperty } = useQuery({
    queryKey: ['property', listing?.property],
    queryFn: () => listingsApi.getProperty(listing!.property),
    enabled: !!listing?.property,
  })

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      await listingsApi.updateProperty(listing!.property, {
        property_type: formData.get('property_type'),
        bedrooms: Number(formData.get('bedrooms')),
        bathrooms: Number(formData.get('bathrooms')),
        floor_area: Number(formData.get('floor_area')),
        description: formData.get('description'),
      })

      await listingsApi.updateListing(listing!.id, {
        title: formData.get('title'),
        price: Number(formData.get('price')),
        description: formData.get('description'),
      })

      for (const file of newFiles) {
        await listingsApi.uploadMedia(listing!.id, file)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manage-listing', id] })
      queryClient.invalidateQueries({ queryKey: ['listings'] })
      navigate(`/dashboard/listings/${id}`)
    },
    onError: (err: any) => setError(err.message || 'Failed to update listing')
  })

  const deleteMediaMutation = useMutation({
    mutationFn: (mediaId: string) => listingsApi.deleteMedia(listing!.id, mediaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manage-listing', id] })
    },
    onError: () => setError('Failed to delete image')
  })

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    mutation.mutate(new FormData(e.currentTarget))
  }

  if (loadingListing || loadingProperty) return <Loading />
  if (!listing || !property) return <div className="p-8"><ErrorMessage message="Data not found." /></div>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <Link to={`/dashboard/listings/${id}`} className="text-sm text-emerald-700 hover:underline mb-4 inline-block">
        ← Back to Manage Listing
      </Link>
      
      <h1 className="text-2xl font-bold mb-6">Edit Listing</h1>
      {error && <ErrorMessage message={error} />}
      
      <form onSubmit={submit} className="bg-white border rounded p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Listing Title</label>
          <input name="title" required defaultValue={listing.title} className="w-full border rounded px-3 py-2" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Property Type</label>
            <select name="property_type" defaultValue={property.property_type} required className="w-full border rounded px-3 py-2">
              <option value="HOUSE">House</option>
              <option value="APARTMENT">Apartment</option>
              <option value="TOWNHOUSE">Townhouse</option>
              <option value="LAND">Land</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Monthly Rent (ZMW)</label>
            <input type="number" name="price" defaultValue={Number(listing.price)} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Bedrooms</label>
            <input type="number" name="bedrooms" defaultValue={property.bedrooms || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Bathrooms</label>
            <input type="number" step="0.5" name="bathrooms" defaultValue={Number(property.bathrooms) || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Floor Area (m²)</label>
            <input type="number" name="floor_area" defaultValue={Number(property.floor_area) || 0} required min="0" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea name="description" defaultValue={listing.description} rows={4} className="w-full border rounded px-3 py-2" />
        </div>

        <div className="border-t pt-4 mt-4">
          <label className="block text-sm font-medium mb-2">Current Images</label>
          <div className="flex gap-3 overflow-x-auto mb-4 p-1">
            {listing.media.map(m => (
              <div key={m.id} className="relative group w-24 h-24 flex-shrink-0">
                <img 
                  src={getMediaUrl(m.file)} 
                  className="w-full h-full object-cover rounded border bg-gray-50" 
                />
                <button
                  type="button"
                  onClick={() => {
                    if (confirm('Delete this image?')) {
                      deleteMediaMutation.mutate(m.id)
                    }
                  }}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition shadow hover:bg-red-600"
                  title="Delete image"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>
            ))}
            {listing.media.length === 0 && <span className="text-gray-400 text-sm">No images yet.</span>}
          </div>

          <label className="block text-sm font-medium mb-1">Upload New Images (Select multiple)</label>
          <input 
            type="file" 
            accept="image/*"
            multiple
            onChange={(e) => setNewFiles(Array.from(e.target.files || []))}
            className="w-full border rounded px-3 py-2" 
          />
        </div>

        <div className="flex gap-4 pt-4 border-t mt-6">
          <Link 
            to={`/dashboard/listings/${id}`} 
            className="flex-1 text-center bg-gray-100 text-gray-700 py-2 rounded hover:bg-gray-200 font-medium transition"
          >
            Cancel
          </Link>
          <button 
            type="submit" 
            disabled={mutation.isPending}
            className="flex-1 bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium transition disabled:opacity-50"
          >
            {mutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
