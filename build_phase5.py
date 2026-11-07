#!/usr/bin/env python3
"""NyumbaLink Phase 5: Monetisation, Wallets, and Contact Unlocking."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- Backend Files

PAYMENTS_APPS = '''
from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
'''

PAYMENTS_MODELS = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0, help_text="Credits available")

    def __str__(self):
        return f"{self.user.email} - {self.balance} credits"

class CreditTransaction(TimeStampedModel):
    class Type(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase Credits"
        UNLOCK = "UNLOCK", "Unlock Contact"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.IntegerField(help_text="Positive for credits added, negative for spent")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=64, blank=True, help_text="PSP Reference ID")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} ({self.amount}) - {self.wallet.user.email}"

class ContactUnlock(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unlocked_contacts")
    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="unlocks")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="uniq_user_listing_unlock"),
        ]

    def __str__(self):
        return f"{self.user.email} unlocked {self.listing.title}"
'''

PAYMENTS_SERVICES = '''
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Wallet, CreditTransaction, ContactUnlock

UNLOCK_COST = 5

def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet

@transaction.atomic
def initiate_credit_purchase(user, amount: int, phone_number: str):
    """Creates a pending transaction. In production, this calls the PSP API."""
    wallet = get_or_create_wallet(user)
    tx = CreditTransaction.objects.create(
        wallet=wallet,
        transaction_type=CreditTransaction.Type.PURCHASE,
        amount=amount,
        status=CreditTransaction.Status.PENDING,
        description=f"Mobile Money Purchase from {phone_number}",
        reference=f"MOCK-{user.id.hex[:8]}-{amount}"
    )
    return tx

@transaction.atomic
def process_payment_webhook(reference: str, success: bool):
    """Mocks the PSP sending a webhook to confirm payment."""
    try:
        tx = CreditTransaction.objects.select_for_update().get(reference=reference)
        if tx.status != CreditTransaction.Status.PENDING:
            return False # Already processed
        
        if success:
            tx.status = CreditTransaction.Status.COMPLETED
            wallet = tx.wallet
            wallet.balance += tx.amount
            wallet.save()
        else:
            tx.status = CreditTransaction.Status.FAILED
        
        tx.save()
        return True
    except CreditTransaction.DoesNotExist:
        return False

@transaction.atomic
def unlock_listing_contact(user, listing):
    wallet = Wallet.objects.select_for_update().get(user=user)
    
    # Check if already unlocked
    if ContactUnlock.objects.filter(user=user, listing=listing).exists():
        return True

    if wallet.balance < UNLOCK_COST:
        raise ValidationError("Insufficient credits.")

    # Deduct credits
    wallet.balance -= UNLOCK_COST
    wallet.save()

    # Log transaction
    CreditTransaction.objects.create(
        wallet=wallet,
        transaction_type=CreditTransaction.Type.UNLOCK,
        amount=-UNLOCK_COST,
        status=CreditTransaction.Status.COMPLETED,
        description=f"Unlocked: {listing.title}"
    )

    # Create unlock record
    ContactUnlock.objects.create(user=user, listing=listing)
    return True
'''

PAYMENTS_VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from apps.properties.models import Listing
from .models import CreditTransaction
from .serializers import WalletSerializer, CreditTransactionSerializer
from . import services

class WalletViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def list(self, request):
        wallet = services.get_or_create_wallet(request.user)
        return Response(self.get_serializer(wallet).data)

    @action(detail=False, methods=["post"])
    def buy(self, request):
        amount = int(request.data.get("amount", 10))
        phone = request.data.get("phone_number", "")
        tx = services.initiate_credit_purchase(request.user, amount, phone)
        return Response({"reference": tx.reference, "status": tx.status})

    @action(detail=False, methods=["post"])
    def mock_webhook(self, request):
        # In production, this is a public endpoint called by MTN/Airtel
        reference = request.data.get("reference")
        success = request.data.get("success", True)
        success = services.process_payment_webhook(reference, success)
        return Response({"processed": success})

class UnlockViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def unlock(self, request):
        listing_id = request.data.get("listing_id")
        try:
            listing = Listing.objects.get(id=listing_id)
            services.unlock_listing_contact(request.user, listing)
            return Response({"status": "unlocked"})
        except ValidationError as e:
            return Response({"detail": str(e.message)}, status=status.HTTP_400_BAD_REQUEST)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=status.HTTP_404_NOT_FOUND)
'''

PAYMENTS_SERIALIZERS = '''
from rest_framework import serializers
from .models import Wallet, CreditTransaction

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("balance",)

class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ("id", "transaction_type", "amount", "status", "description", "created_at")
'''

PAYMENTS_URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, UnlockViewSet

router = DefaultRouter()
router.register("wallet", WalletViewSet, basename="wallet")
router.register("unlock", UnlockViewSet, basename="unlock")

urlpatterns = router.urls
'''

# ---------------------------------------------------------------- Frontend Files

FRONTEND_PAYMENTS_API = '''
import { api } from './client'

export const paymentsApi = {
  getWallet: () => api<{ balance: number }>('/wallet/'),
  buyCredits: (amount: number, phone: string) => 
    api<{ reference: string }>('/wallet/buy/', {
      method: 'POST',
      body: JSON.stringify({ amount, phone_number: phone })
    }),
  mockWebhook: (reference: string) => 
    api('/wallet/mock_webhook/', {
      method: 'POST',
      body: JSON.stringify({ reference, success: true })
    }),
  unlockListing: (listingId: string) => 
    api('/unlock/unlock/', {
      method: 'POST',
      body: JSON.stringify({ listing_id: listingId })
    })
}
'''

WALLET_PAGE = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { paymentsApi } from '../api/payments'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

export default function WalletPage() {
  const queryClient = useQueryClient()
  const [phone, setPhone] = useState('')
  const [amount, setAmount] = useState(10)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const { data: wallet, isLoading } = useQuery({
    queryKey: ['wallet'],
    queryFn: paymentsApi.getWallet,
  })

  const buyMutation = useMutation({
    mutationFn: () => paymentsApi.buyCredits(amount, phone),
    onSuccess: async (data) => {
      setSuccessMsg('Processing payment... (simulating Mobile Money prompt)')
      setError('')
      
      // Simulate the PSP taking 2 seconds to confirm
      setTimeout(async () => {
        try {
          await paymentsApi.mockWebhook(data.reference)
          queryClient.invalidateQueries({ queryKey: ['wallet'] })
          setSuccessMsg(`Successfully bought ${amount} credits!`)
        } catch {
          setError('Payment failed.')
          setSuccessMsg('')
        }
      }, 2000)
    },
    onError: (err: any) => setError(err.message)
  })

  if (isLoading) return <Loading />

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Your Wallet</h1>
      
      <div className="bg-emerald-600 text-white p-6 rounded-lg mb-8 text-center">
        <p className="text-emerald-100 mb-1">Available Credits</p>
        <p className="text-5xl font-bold">{wallet?.balance || 0}</p>
      </div>

      {error && <ErrorMessage message={error} />}
      {successMsg && (
        <div className="bg-green-50 text-green-700 p-3 rounded mb-4 text-sm">{successMsg}</div>
      )}

      <div className="bg-white border rounded-lg p-6">
        <h2 className="font-bold mb-4">Buy Credits</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Amount</label>
            <select 
              value={amount} onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full border rounded px-3 py-2"
            >
              <option value={10}>10 Credits</option>
              <option value={20}>20 Credits</option>
              <option value={50}>50 Credits</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Mobile Money Number</label>
            <input 
              type="text" placeholder="e.g. 0977123456" 
              value={phone} onChange={(e) => setPhone(e.target.value)}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          <button 
            onClick={() => buyMutation.mutate()}
            disabled={buyMutation.isPending || !phone}
            className="w-full bg-gray-900 text-white py-2 rounded hover:bg-black disabled:opacity-50"
          >
            {buyMutation.isPending ? 'Initiating...' : 'Pay with Mobile Money'}
          </button>
        </div>
      </div>
    </div>
  )
}
'''

DETAIL_PAGE = '''
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listingsApi, getMediaUrl } from '../api/listings'
import { paymentsApi } from '../api/payments'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import ImageLightbox from '../components/ImageLightbox'

export default function ListingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [unlockError, setUnlockError] = useState('')

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

  if (isLoading) return <Loading />
  if (error || !listing) return <div className="p-8"><ErrorMessage message="Listing not found." /></div>

  const images = listing.media.filter((m) => m.media_type === 'IMAGE')
  
  // In a real app, this would come from the backend!
  // (e.g., listing.is_unlocked = true)
  const isUnlocked = false // Placeholder until we wire the backend flag

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/" className="text-sm text-emerald-700 hover:underline">← Back to listings</Link>
      <h1 className="text-3xl font-bold mt-4 mb-2">{listing.title}</h1>
      <p className="text-gray-600 mb-6">{listing.property_summary.neighbourhood} · {listing.property_summary.property_type}</p>

      {images.length > 0 && (
        <div className="grid gap-2 mb-6" style={{ gridTemplateColumns: images.length > 1 ? '2fr 1fr' : '1fr' }}>
          {images.slice(0, 2).map((m, idx) => (
            <div key={m.id} className="relative cursor-pointer group overflow-hidden rounded-lg" onClick={() => setLightboxIndex(idx)}>
              <img src={getMediaUrl(m.file)} className="w-full h-64 md:h-80 object-cover group-hover:opacity-90 transition" />
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <h2 className="font-semibold text-lg mb-2">Description</h2>
          <p className="whitespace-pre-line text-gray-700">{listing.description || 'No description provided.'}</p>
        </div>
        
        <aside className="border rounded-lg p-4 h-fit bg-white shadow-sm">
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
          ) : isUnlocked ? (
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded text-center">
              <p className="text-sm text-emerald-800 font-medium mb-1">Contact Details</p>
              <p className="font-bold text-lg">+260 97 123 4567</p>
              <p className="text-xs text-emerald-600 mt-1">{listing.created_by_email}</p>
            </div>
          ) : (
            <div>
              {unlockError && <p className="text-xs text-red-600 mb-2">{unlockError}</p>}
              <button 
                onClick={() => unlockMutation.mutate()}
                disabled={unlockMutation.isPending}
                className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium disabled:opacity-50"
              >
                {unlockMutation.isPending ? 'Unlocking...' : 'Unlock Contact (5 Credits)'}
              </button>
              <Link to="/wallet" className="block text-center text-xs text-emerald-700 mt-2 hover:underline">
                Top up wallet
              </Link>
            </div>
          )}
          <p className="text-xs text-gray-500 mt-4 text-center">Advertised by {listing.created_by_email}</p>
        </aside>
      </div>

      {lightboxIndex !== null && (
        <ImageLightbox images={images} initialIndex={lightboxIndex} onClose={() => setLightboxIndex(null)} />
      )}
    </div>
  )
}
'''

LAYOUT = '''
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">NyumbaLink</Link>
          <nav className="flex items-center gap-4 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className="text-gray-700 hover:text-emerald-700">Dashboard</Link>
                <Link to="/verification" className="text-gray-700 hover:text-emerald-700">Verification</Link>
                <Link to="/wallet" className="text-gray-700 font-medium hover:text-emerald-700">Wallet</Link>
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                <button onClick={() => { logout(); navigate('/') }} className="text-red-600 hover:underline">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700">Register</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1"><Outlet /></main>
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">NyumbaLink · Find your place. Connect your world.</footer>
    </div>
  )
}
'''

APP_TSX = '''
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ListingDetailPage from './pages/ListingDetailPage'
import NotFoundPage from './pages/NotFoundPage'
import DashboardPage from './pages/DashboardPage'
import CreateListingPage from './pages/CreateListingPage'
import ManageListingPage from './pages/ManageListingPage'
import EditListingPage from './pages/EditListingPage'
import VerificationPage from './pages/VerificationPage'
import WalletPage from './pages/WalletPage'
import ProtectedRoute from './auth/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="/listings/:id" element={<ListingDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/listings/new" element={<CreateListingPage />} />
          <Route path="/dashboard/listings/:id" element={<ManageListingPage />} />
          <Route path="/dashboard/listings/:id/edit" element={<EditListingPage />} />
          <Route path="/verification" element={<VerificationPage />} />
          <Route path="/wallet" element={<WalletPage />} />
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

FRONTEND_FILES = {
    "src/api/payments.ts": FRONTEND_PAYMENTS_API,
    "src/pages/WalletPage.tsx": WALLET_PAGE,
    "src/pages/ListingDetailPage.tsx": DETAIL_PAGE,
    "src/components/Layout.tsx": LAYOUT,
    "src/App.tsx": APP_TSX,
}

BACKEND_FILES = {
    "apps/payments/__init__.py": "",
    "apps/payments/apps.py": PAYMENTS_APPS,
    "apps/payments/models.py": PAYMENTS_MODELS,
    "apps/payments/services.py": PAYMENTS_SERVICES,
    "apps/payments/views.py": PAYMENTS_VIEWS,
    "apps/payments/serializers.py": PAYMENTS_SERIALIZERS,
    "apps/payments/urls.py": PAYMENTS_URLS,
    "apps/payments/admin.py": "from django.contrib import admin\nfrom .models import Wallet, CreditTransaction, ContactUnlock\n\n@admin.register(Wallet)\nclass WalletAdmin(admin.ModelAdmin):\n    list_display = ('user', 'balance')\n\n@admin.register(CreditTransaction)\nclass CreditTransactionAdmin(admin.ModelAdmin):\n    list_display = ('wallet', 'transaction_type', 'amount', 'status', 'created_at')\n\n@admin.register(ContactUnlock)\nclass ContactUnlockAdmin(admin.ModelAdmin):\n    list_display = ('user', 'listing', 'created_at')\n",
    "apps/payments/migrations/__init__.py": "",
}

def run():
    print(f"NyumbaLink Phase 5 (Monetisation) -> {ROOT}\n")
    
    print("Writing backend files:")
    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nPatching settings and urls:")
    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.payments"' not in text:
        text = text.replace('    "apps.verification",\n', '    "apps.verification",\n    "apps.payments",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")
    
    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.payments.urls")' not in text:
        text = text.replace('path("api/v1/", include("apps.verification.urls")),\n', 'path("api/v1/", include("apps.verification.urls")),\n    path("api/v1/", include("apps.payments.urls")),\n')
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nWriting frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "payments"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 5 Complete.

Next steps to test the full flow:

  1. Restart frontend (npm run dev).
  2. Log in as demo@nyumbalink.com.
  3. Click "Wallet" in the header.
  4. Enter a dummy phone number (e.g. 0977123456) and click "Pay". 
     (It will simulate a 2-second Mobile Money delay, then auto-confirm the webhook).
  5. Your balance will jump to 10 Credits.
  6. Go to a public listing (e.g. the Woodlands Apartment).
  7. Instead of "Contact Advertiser", you will see "Unlock Contact (5 Credits)".
  8. Click it. The balance drops to 5, and the landlord's phone number replaces the button.
  9. Refresh the page. The contact details stay unlocked (because the backend remembers).
""")

if __name__ == "__main__":
    run()