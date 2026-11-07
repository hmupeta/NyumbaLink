import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Link } from 'react-router-dom'
import { getMediaUrl } from '../api/listings'
import type { Listing } from '../api/types'

// Fix missing marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Custom Price Pin CSS
const createPriceIcon = (price: string, currency: string) => {
  return L.divIcon({
    className: 'custom-price-pin',
    html: `<div class="bg-emerald-600 text-white font-bold px-3 py-1 rounded-full text-sm shadow-md border-2 border-white whitespace-nowrap hover:bg-emerald-700 transition cursor-pointer">
            ${currency} ${Number(price).toLocaleString()}
           </div>`,
    iconSize: [80, 30],
    iconAnchor: [40, 15],
  })
}

// Component to recenter map when listings change
function MapBounds({ listings }: { listings: Listing[] }) {
  const map = useMap()
  useEffect(() => {
    const validListings = listings.filter(l => l.property_summary?.latitude && l.property_summary?.longitude)
    if (validListings.length > 0) {
      const bounds = L.latLngBounds(
        validListings.map(l => [l.property_summary.latitude!, l.property_summary.longitude!])
      )
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 })
    }
  }, [listings, map])
  return null
}

export default function MapView({ listings }: { listings: Listing[] }) {
  const validListings = listings.filter(l => l.property_summary?.latitude && l.property_summary?.longitude)
  
  // Default to Lusaka center
  const defaultCenter: [number, number] = [-15.416, 28.283]

  return (
    <div className="w-full h-[calc(100vh-140px)] rounded-lg overflow-hidden shadow-inner border relative z-0">
      <MapContainer center={defaultCenter} zoom={12} scrollWheelZoom={true} className="w-full h-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapBounds listings={validListings} />
        {validListings.map((listing) => (
          <Marker
            key={listing.id}
            position={[listing.property_summary.latitude!, listing.property_summary.longitude!]}
            icon={createPriceIcon(listing.price, listing.currency)}
          >
            <Popup className="zillow-popup">
              <Link to={`/listings/${listing.id}`} className="block w-48 no-underline text-black">
                <img 
                  src={listing.media[0] ? getMediaUrl(listing.media[0].file) : ''} 
                  className="w-full h-24 object-cover rounded-t-md mb-2" 
                  alt={listing.title} 
                />
                <div className="p-1">
                  <p className="font-bold text-sm m-0 truncate">{listing.title}</p>
                  <p className="text-xs text-gray-500 m-0">{listing.property_summary.neighbourhood}</p>
                  <p className="text-emerald-700 font-bold text-sm mt-1 m-0">
                    {listing.currency} {Number(listing.price).toLocaleString()}
                  </p>
                </div>
              </Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
