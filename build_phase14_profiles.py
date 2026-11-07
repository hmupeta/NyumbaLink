#!/usr/bin/env python3
"""NyumbaLink Phase 14: Public Landlord Profiles & Reviews."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Files

REVIEWS_MODELS = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Review(TimeStampedModel):
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given")
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()

    class Meta(TimeStampedModel.Meta):
        constraints = [
            # A user can only review a landlord once
            models.UniqueConstraint(fields=["landlord", "reviewer"], name="uniq_landlord_reviewer"),
        ]

    def __str__(self):
        return f"{self.rating}★ for {self.landlord.email} by {self.reviewer.email}"
'''

REVIEWS_SERIALIZERS = '''
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Review
from apps.properties.models import Listing
from apps.properties.serializers import ListingSerializer

User = get_user_model()

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.first_name", read_only=True)
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "landlord", "reviewer", "reviewer_name", "reviewer_email", "rating", "comment", "created_at")
        read_only_fields = ("id", "landlord", "reviewer", "created_at")

class PublicProfileSerializer(serializers.ModelSerializer):
    listings = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "listings", "reviews", "average_rating", "verification_status")

    def get_listings(self, obj):
        # Only show published listings for this landlord
        listings = Listing.objects.filter(created_by=obj, status="PUBLISHED")
        # We pass context so the ListingSerializer can process is_saved correctly
        return ListingSerializer(listings, many=True, context=self.context).data

    def get_reviews(self, obj):
        reviews = obj.reviews_received.all().order_by("-created_at")
        return ReviewSerializer(reviews, many=True).data

    def get_average_rating(self, obj):
        reviews = obj.reviews_received.all()
        if not reviews: return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_verification_status(self, obj):
        # Check if they have an approved IDENTITY verification
        has_id = obj.verification_cases.filter(verification_type="IDENTITY", status="APPROVED").exists()
        return {"identity": has_id}
'''

REVIEWS_VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Review
from .serializers import ReviewSerializer, PublicProfileSerializer

User = get_user_model()

class PublicProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = PublicProfileSerializer(user, context={"request": request})
        return Response(serializer.data)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post", "get", "head", "options"]

    def get_queryset(self):
        return Review.objects.filter(landlord_id=self.kwargs.get("profile_pk"))

    def perform_create(self, serializer):
        landlord_id = self.kwargs.get("profile_pk")
        if str(self.request.user.id) == str(landlord_id):
            raise permissions.PermissionDenied("You cannot review yourself.")
        
        # Check if already reviewed
        if Review.objects.filter(landlord_id=landlord_id, reviewer=self.request.user).exists():
            raise permissions.PermissionDenied("You have already reviewed this landlord.")

        serializer.save(landlord_id=landlord_id, reviewer=self.request.user)
'''

REVIEWS_URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import PublicProfileViewSet, ReviewViewSet

router = DefaultRouter()
router.register("profiles", PublicProfileViewSet, basename="profile")

# Nested router for reviews under profiles
profile_router = routers.NestedDefaultRouter(router, "profiles", lookup="profile")
profile_router.register("reviews", ReviewViewSet, basename="profile-reviews")

urlpatterns = router.urls + profile_router.urls
'''

# ---------------------------------------------------------------- 2. Frontend Files

FRONTEND_API = '''
import { api } from './client'

export const profileApi = {
  get: (userId: string) => api<any>(`/profiles/${userId}/`),
  leaveReview: (userId: string, rating: number, comment: string) => 
    api(`/profiles/${userId}/reviews/`, {
      method: 'POST',
      body: JSON.stringify({ rating, comment })
    })
}
'''

PROFILE_PAGE = '''
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { profileApi } from '../api/profile'
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

  if (isLoading) return <Loading />
  if (fetchError || !profile) return <div className="p-8"><ErrorMessage message="Profile not found." /></div>

  const isOwnProfile = user?.id === profile.id

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      
      {/* Profile Header */}
      <div className="bg-white border rounded-xl p-8 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8">
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
          
          <div className="flex items-center gap-2">
            <div className="flex text-yellow-500">
              {[1,2,3,4,5].map(star => (
                <svg key={star} width="20" height="20" viewBox="0 0 24 24" fill={star <= (profile.average_rating || 0) ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
              ))}
            </div>
            <span className="font-bold text-gray-800">{profile.average_rating || 'No reviews'}</span>
            <span className="text-gray-500 text-sm">({profile.reviews.length} reviews)</span>
          </div>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-lg border text-center min-w-[150px]">
          <p className="text-3xl font-bold text-emerald-700">{profile.listings.length}</p>
          <p className="text-sm text-gray-600 font-medium">Active Listings</p>
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

          {/* Leave a Review Form */}
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
    </div>
  )
}
'''

# Patch ListingDetailPage to link to the profile
DETAIL_FILE = FRONTEND / "src" / "pages" / "ListingDetailPage.tsx"
text = DETAIL_FILE.read_text(encoding="utf-8")
if "PublicProfilePage" not in text and "advertiser profile" not in text:
    old_advertiser = '''<p className="text-xs text-gray-500 mt-4 text-center">Advertised by {listing.created_by_email}</p>'''
    new_advertiser = '''<p className="text-xs text-gray-500 mt-4 text-center">
            Advertised by <Link to={`/profiles/${listing.created_by}`} className="text-emerald-700 hover:underline font-medium">View Landlord Profile</Link>
          </p>'''
    
    if old_advertiser in text:
        text = text.replace(old_advertiser, new_advertiser)
    else:
        # Fallback if the exact string isn't found
        text = text.replace(
            'Advertised by {listing.created_by_email}',
            'Advertised by <Link to={`/profiles/${listing.created_by}`} className="text-emerald-700 hover:underline font-medium">View Landlord Profile</Link>'
        )
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("Patched ListingDetailPage.tsx to link to Public Profile")

# Patch App.tsx
APP_FILE = FRONTEND / "src" / "App.tsx"
text = APP_FILE.read_text(encoding="utf-8")
if "PublicProfilePage" not in text:
    text = text.replace(
        "import IntentCards from './components/IntentCards'", # Just to find a line
        "import IntentCards from './components/IntentCards'" # Dummy
    ) # Actually let's insert the import
    text = text.replace(
        "import SavedPropertiesPage from './pages/SavedPropertiesPage'",
        "import SavedPropertiesPage from './pages/SavedPropertiesPage'\nimport PublicProfilePage from './pages/PublicProfilePage'"
    )
    text = text.replace(
        '<Route path="/listings/:id" element={<ListingDetailPage />} />',
        '<Route path="/listings/:id" element={<ListingDetailPage />} />\n        <Route path="/profiles/:id" element={<PublicProfilePage />} />'
    )
    APP_FILE.write_text(text, encoding="utf-8")
    print("Patched App.tsx to include PublicProfilePage route")

# ---------------------------------------------------------------- 3. Execution

BACKEND_FILES = {
    "apps/reviews/__init__.py": "",
    "apps/reviews/apps.py": "from django.apps import AppConfig\n\nclass ReviewsConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.reviews'\n    label = 'reviews'\n",
    "apps/reviews/models.py": REVIEWS_MODELS.strip() + "\n",
    "apps/reviews/serializers.py": REVIEWS_SERIALIZERS.strip() + "\n",
    "apps/reviews/views.py": REVIEWS_VIEWS.strip() + "\n",
    "apps/reviews/urls.py": REVIEWS_URLS.strip() + "\n",
    "apps/reviews/admin.py": "from django.contrib import admin\nfrom .models import Review\nadmin.site.register(Review)\n",
    "apps/reviews/migrations/__init__.py": "",
}

FRONTEND_FILES = {
    "src/api/profile.ts": FRONTEND_API,
    "src/pages/PublicProfilePage.tsx": PROFILE_PAGE,
}

def run():
    print(f"NyumbaLink Phase 14 (Profiles & Reviews) -> {ROOT}\n")

    print("Writing backend files:")
    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nPatching settings and urls:")
    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.reviews"' not in text:
        text = text.replace('    "apps.messaging",\n', '    "apps.messaging",\n    "apps.reviews",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.reviews.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.messaging.urls")),\n',
            'path("api/v1/", include("apps.messaging.urls")),\n    path("api/v1/", include("apps.reviews.urls")),\n'
        )
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nWriting frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  {rel}")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "reviews"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 14 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as the seeker, go to a listing, and click "View Landlord Profile" at the bottom of the contact card.
  3. You will be taken to the Landlord's public profile (showing their active listings and verification badge).
  4. Scroll down to "Leave a Review", give 5 stars, and submit.
  5. The review will appear instantly!
  6. You can also log in as the demo landlord to see their profile page.
""")

if __name__ == "__main__":
    run()