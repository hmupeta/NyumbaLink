export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
}

export interface ListingMedia {
  id: string
  file: string
  media_type: 'IMAGE' | 'VIDEO' | 'TOUR'
  caption: string
  display_order: number
}

export interface PropertySummary {
  id: string
  property_type: string
  bedrooms: number | null
  bathrooms: string | null
  neighbourhood: string
  latitude: number | null
  longitude: number | null
}

export interface Listing {
  id: string
  property: string
  property_summary: PropertySummary
  created_by: string
  created_by_email: string
  transaction_type: 'RENT' | 'SALE' | 'SHORT_LET'
  price: string
  currency: string
  price_period: 'MONTH' | 'YEAR' | 'ONCE'
  deposit_months: string | null
  title: string
  description: string
  available_from: string | null
  status: string
  published_at: string | null
  expires_at: string | null
  media: ListingMedia[]
  created_at: string
  updated_at: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
