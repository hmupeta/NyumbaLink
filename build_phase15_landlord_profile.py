#!/usr/bin/env python3
"""NyumbaLink Phase 15: Landlord Cover Photos, Avatars, and Edit Profile."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Models
MODELS_FILE = ROOT / "apps" / "accounts" / "models.py"
text = MODELS_FILE.read_text(encoding="utf-8")

if "cover_photo" not in text:
    # Add fields to the User model
    old_fields = '''    phone_verified_at = models.DateTimeField(blank=True, null=True)'''
    new_fields = '''    phone_verified_at = models.DateTimeField(blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover_photo = models.ImageField(upload_to="covers/", blank=True, null=True)
    bio = models.TextField(blank=True, help_text="Tell tenants a bit about yourself.")'''
    
    text = text.replace(old_fields, new_fields)
    MODELS_FILE.write_text(text, encoding="utf-8")
    print("Patched accounts/models.py: added avatar, cover_photo, bio")

# ---------------------------------------------------------------- 2. Backend: Serializers & Views
ACCOUNTS_SERIALIZERS = ROOT / "apps" / "accounts" / "serializers.py"
text = ACCOUNTS_SERIALIZERS.read_text(encoding="utf-8")
if "avatar" not in text:
    old_user = '''        fields = ("id", "email", "first_name", "last_name", "is_staff")'''
    new_user = '''        fields = ("id", "email", "first_name", "last_name", "is_staff", "avatar", "cover_photo", "bio")'''
    text = text.replace(old_user, new_user)
    ACCOUNTS_SERIALIZERS.write_text(text, encoding="utf-8")
    print("Patched accounts/serializers.py: added profile fields")

# Update MeView to allow PATCH requests for profile updates
ACCOUNTS_VIEWS = ROOT / "apps" / "accounts" / "views.py"
text = ACCOUNTS_VIEWS.read_text(encoding="utf-8")
if "def patch(self, request):" not in text:
    old_me = '''class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)'''
    
    new_me = '''class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        for field in ["first_name", "last_name", "bio"]:
            if field in request.data:
                setattr(user, field, request.data[field])
        if "avatar" in request.FILES:
            user.avatar = request.FILES["avatar"]
        if "cover_photo" in request.FILES:
            user.cover_photo = request.FILES["cover_photo"]
        user.save()
        return Response(UserSerializer(user).data)'''
    
    text = text.replace(old_me, new_me)
    ACCOUNTS_VIEWS.write_text(text, encoding="utf-8")
    print("Patched accounts/views.py: enabled PATCH on MeView")

# Update Reviews PublicProfileSerializer
REVIEWS_SERIALIZERS = ROOT / "apps" / "reviews" / "serializers.py"
text = REVIEWS_SERIALIZERS.read_text(encoding="utf-8")
if "cover_photo" not in text:
    old_profile = '''        fields = ("id", "first_name", "last_name", "email", "listings", "reviews", "average_rating", "verification_status")'''
    new_profile = '''        fields = ("id", "first_name", "last_name", "email", "avatar", "cover_photo", "bio", "listings", "reviews", "average_rating", "verification_status")'''
    text = text.replace(old_profile, new_profile)
    REVIEWS_SERIALIZERS.write_text(text, encoding="utf-8")
    print("Patched reviews/serializers.py: exposed profile fields")

# ---------------------------------------------------------------- 3. Frontend API
PROFILE_API = '''
import { api } from './client'

export const profileApi = {
  get: (userId: string) => api<any>(`/profiles/${userId}/`),
  leaveReview: (userId: string, rating: number, comment: string) => 
    api(`/profiles/${userId}/reviews/`, {
      method: 'POST',
      body: JSON.stringify({ rating, comment })
    }),
  updateProfile: (data: FormData) => {
    // Using fetch directly because our api helper defaults to JSON
    return fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/me/`, {
      method: 'PATCH',
      credentials: 'include',
      body: data
    }).then(res => {
      if (!res.ok) throw new Error('Failed to update profile');
      return res.json();
    })
  }
}
'''
(FRONTEND / "src" / "api" / "profile.ts").write_text(PROFILE_API.strip() + "\n", encoding="utf-8")
print("Patched src/api/profile.ts: added updateProfile")

# ---------------------------------------------------------------- 4. Frontend Profile Page
PROFILE_PAGE = '''
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { profileApi } from '../api/profile'
import { getMediaUrl } from '../api/listings'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ListingGrid from '../components/ListingGrid'

export default function PublicProfilePage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [showEditModal, setShowEditModal] = useState(false)

  const { data: profile, isLoading, error: fetchError } = useQuery({
    queryKey: ['profile', id],
    queryFn: () => profileApi.get(id!),
    enabled: !!id,
  })

  const reviewMutation = useMutation({
    mutationFn: () => profileApi.leaveReview(id!, rating, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile', id] })
      setComment('')
      setError('')
      alert('Review submitted successfully!')
    },
    onError: (err: any) => setError(err.message || 'Failed to submit review.')
  })

  const editMutation = useMutation({
    mutationFn: (formData: FormData) => profileApi.updateProfile(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile', id] })
      setShowEditModal(false)
    },
    onError: () => alert('Failed to update profile.')
  })

  const handleEditSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    editMutation.mutate(fd)
  }

  if (isLoading) return <Loading />
  if (fetchError || !profile) return <div className="p-8"><ErrorMessage message="Profile not found." /></div>

  const isOwnProfile = user?.id === profile.id

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      
      {/* Profile Header with Cover & Avatar */}
      <div className="bg-white border rounded-xl shadow-sm mb-8 overflow-hidden">
        {/* Cover Photo */}
        <div className="h-48 w-full bg-slate-200 relative">
          {profile.cover_photo ? (
            <img src={getMediaUrl(profile.cover_photo)} className="w-full h-full object-cover" alt="Cover" />
          ) : (
            <div className="w-full h-full bg-gradient-to-r from-emerald-600 to-teal-700"></div>
          )}
        </div>

        {/* Avatar & Info */}
        <div className="px-8 pb-8 relative">
          {/* Avatar */}
          <div className="absolute -top-16 w-32 h-32 rounded-full border-4 border-white bg-white shadow-md overflow-hidden flex items-center justify-center text-4xl font-bold text-emerald-600">
            {profile.avatar ? (
              <img src={getMediaUrl(profile.avatar)} className="w-full h-full object-cover" alt="Avatar" />
            ) : (
              profile.first_name ? profile.first_name[0] : 'N'
            )}
          </div>

          <div className="pt-20 flex flex-col md:flex-row justify-between items-start gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold">
                  {profile.first_name ? `${profile.first_name} ${profile.last_name}` : 'NyumbaLink Landlord'}
                </h1>
                {profile.verification_status.identity && (
                  <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    ID Verified
                  </span>
                )}
              </div>
              <p className="text-gray-600 mb-2">{profile.email}</p>
              
              <div className="flex items-center gap-2 mb-4">
                <div className="flex text-yellow-500">
                  {[1,2,3,4,5].map(star => (
                    <svg key={star} width="20" height="20" viewBox="0 0 24 24" fill={star <= (profile.average_rating || 0) ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                  ))}
                </div>
                <span className="font-bold text-gray-800">{profile.average_rating || 'No reviews'}</span>
                <span className="text-gray-500 text-sm">({profile.reviews.length} reviews)</span>
              </div>

              {profile.bio && <p className="text-gray-700 max-w-2xl">{profile.bio}</p>}
            </div>

            <div className="flex gap-4 items-center">
              {isOwnProfile && (
                <button onClick={() => setShowEditModal(true)} className="px-4 py-2 border rounded hover:bg-gray-50 font-medium text-sm transition">
                  Edit Profile
                </button>
              )}
              <div className="bg-gray-50 px-6 py-4 rounded-lg border text-center shadow-sm">
                <p className="text-3xl font-bold text-emerald-700">{profile.listings.length}</p>
                <p className="text-sm text-gray-600 font-medium">Active Listings</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        
        {/* Left Side: Listings */}
        <div className="md:col-span-2">
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Properties by this Landlord</h2>
          {profile.listings.length > 0 ? (
            <ListingGrid listings={profile.listings} />
          ) : (
            <p className="text-gray-500">This landlord has no active listings right now.</p>
          )}
        </div>

        {/* Right Side: Reviews */}
        <div>
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Reviews</h2>
          
          <div className="space-y-4 mb-8">
            {profile.reviews.length === 0 && <p className="text-gray-500 text-sm">No reviews yet.</p>}
            {profile.reviews.map((r: any) => (
              <div key={r.id} className="bg-white p-4 rounded border shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-sm">{r.reviewer_name || r.reviewer_email.split('@')[0]}</span>
                  <div className="flex text-yellow-500">
                    {[...Array(r.rating)].map((_, i) => (
                      <svg key={i} width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                    ))}
                  </div>
                </div>
                <p className="text-sm text-gray-600">{r.comment}</p>
              </div>
            ))}
          </div>

          {user && !isOwnProfile && !profile.reviews.find((r: any) => r.reviewer === user.id) && (
            <div className="bg-gray-50 border rounded p-4">
              <h3 className="font-bold text-sm mb-3">Leave a Review</h3>
              {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
              <div className="flex gap-1 mb-3">
                {[1,2,3,4,5].map(star => (
                  <button key={star} onClick={() => setRating(star)} className={`text-2xl ${star <= rating ? 'text-yellow-500' : 'text-gray-300'}`}>★</button>
                ))}
              </div>
              <textarea 
                value={comment} onChange={e => setComment(e.target.value)}
                placeholder="Share your experience renting from this landlord..." 
                className="w-full border rounded px-3 py-2 text-sm mb-3" rows={3}
              />
              <button 
                onClick={() => reviewMutation.mutate()}
                disabled={!comment.trim() || reviewMutation.isPending}
                className="w-full bg-emerald-600 text-white py-2 rounded font-medium hover:bg-emerald-700 disabled:opacity-50 text-sm"
              >
                Submit Review
              </button>
            </div>
          )}
        </div>

      </div>

      {/* Edit Profile Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Edit Profile</h2>
              <button onClick={() => setShowEditModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleEditSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">First Name</label>
                <input name="first_name" defaultValue={profile.first_name} className="w-full border rounded px-3 py-2" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Last Name</label>
                <input name="last_name" defaultValue={profile.last_name} className="w-full border rounded px-3 py-2" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Bio</label>
                <textarea name="bio" defaultValue={profile.bio} rows={3} className="w-full border rounded px-3 py-2" placeholder="Tell tenants about yourself..." />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Cover Photo</label>
                <input type="file" name="cover_photo" accept="image/*" className="w-full text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Profile Avatar</label>
                <input type="file" name="avatar" accept="image/*" className="w-full text-sm" />
              </div>
              <button 
                type="submit" 
                disabled={editMutation.isPending}
                className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 mt-4 font-medium"
              >
                {editMutation.isPending ? 'Saving...' : 'Save Profile'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
'''

(FRONTEND / "src" / "pages" / "PublicProfilePage.tsx").write_text(PROFILE_PAGE.strip() + "\n", encoding="utf-8")
print("Patched PublicProfilePage.tsx: added cover, avatar, and edit modal")

# ---------------------------------------------------------------- 5. Run Migrations
print("\nApplying database migrations...")
subprocess.run([sys.executable, "manage.py", "makemigrations", "accounts"])
subprocess.run([sys.executable, "manage.py", "migrate"])

print("""
Phase 15 Complete!

Test the flow:
  1. Restart backend and frontend.
  2. Log in as demo@nyumbalink.com (the landlord).
  3. Go to a listing and click "View Landlord Profile" at the bottom.
  4. Click "Edit Profile".
  5. Upload a Cover Photo and an Avatar. Add a short Bio. Save.
  6. The profile page will instantly transform with a Zillow-style cover photo, circular avatar, and bio!
""")