import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { listingsApi } from '../api/listings'
import ErrorMessage from '../components/ErrorMessage'

export default function CreateListingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const { data: hoods } = useQuery({
    queryKey: ['neighbourhoods'],
    queryFn: () => api<any>('/neighbourhoods/?page=1'),
  })

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const property = await listingsApi.createProperty({
        neighbourhood: formData.get('neighbourhood'),
        property_type: formData.get('property_type'),
        bedrooms: Number(formData.get('bedrooms')),
        bathrooms: Number(formData.get('bathrooms')),
        floor_area: Number(formData.get('floor_area')),
        description: formData.get('description'),
      })

      const listing = await listingsApi.createListing({
        property: property.id,
        transaction_type: 'RENT',
        price: Number(formData.get('price')),
        title: formData.get('title'),
        description: formData.get('description'),
      })

      if (file) {
        await listingsApi.uploadMedia(listing.id, file)
      }
      
      return listing
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-listings'] })
      navigate('/dashboard')
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to create listing')
    }
  })

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    const formData = new FormData(e.currentTarget)
    mutation.mutate(formData)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Back Link */}
      <Link to="/dashboard" className="text-sm text-emerald-700 hover:underline mb-4 inline-block">
        ← Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold mb-6">Create a New Listing</h1>
      {error && <ErrorMessage message={error} />}
      
      <form onSubmit={submit} className="bg-white border rounded p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Listing Title</label>
          <input name="title" required className="w-full border rounded px-3 py-2" placeholder="e.g. Modern 2-Bed Apartment" />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Property Type</label>
            <select name="property_type" required className="w-full border rounded px-3 py-2">
              <option value="HOUSE">House</option>
              <option value="APARTMENT">Apartment</option>
              <option value="TOWNHOUSE">Townhouse</option>
              <option value="LAND">Land</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Neighbourhood</label>
            <select name="neighbourhood" required className="w-full border rounded px-3 py-2">
              <option value="">Select location...</option>
              {hoods?.results.map((h: any) => (
                <option key={h.id} value={h.id}>{h.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Bedrooms</label>
            <input type="number" name="bedrooms" required min="0" defaultValue="2" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Bathrooms</label>
            <input type="number" step="0.5" name="bathrooms" required min="0" defaultValue="1" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Floor Area (m²)</label>
            <input type="number" name="floor_area" required min="0" defaultValue="80" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Monthly Rent (ZMW)</label>
            <input type="number" name="price" required min="0" defaultValue="5000" className="w-full border rounded px-3 py-2" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea name="description" rows={4} className="w-full border rounded px-3 py-2" placeholder="Describe the property..." />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Cover Image</label>
          <input 
            type="file" 
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full border rounded px-3 py-2" 
          />
        </div>

        <div className="flex gap-4 pt-4">
          <Link 
            to="/dashboard" 
            className="flex-1 text-center bg-gray-100 text-gray-700 py-2 rounded hover:bg-gray-200 font-medium transition"
          >
            Cancel
          </Link>
          <button 
            type="submit" 
            disabled={mutation.isPending}
            className="flex-1 bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium transition disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating...' : 'Create Listing'}
          </button>
        </div>
      </form>
    </div>
  )
}
