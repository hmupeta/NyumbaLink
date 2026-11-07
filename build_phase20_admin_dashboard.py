#!/usr/bin/env python3
"""NyumbaLink Phase 20: Platform Admin Dashboard (God-View)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend View
# We put this in the core app so it doesn't require a new migration
CORE_VIEWS = ROOT / "apps" / "core" / "views.py"
text = CORE_VIEWS.read_text(encoding="utf-8")

if "class AdminDashboardView" not in text:
    # Add imports
    text = text.replace(
        "from django.http import JsonResponse",
        "from django.http import JsonResponse\nfrom rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom rest_framework.permissions import IsAdminUser\nfrom django.db.models import Sum\nfrom django.contrib.auth import get_user_model\nfrom apps.properties.models import Listing, Report\nfrom apps.payments.models import CreditTransaction, ContactUnlock\nfrom apps.verification.models import VerificationCase\n\nUser = get_user_model()"
    )
    
    # Add the view
    text += '''

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Platform Stats
        total_users = User.objects.count()
        total_active_listings = Listing.objects.filter(status="PUBLISHED").count()
        
        # Moderation Alerts
        pending_listings = Listing.objects.filter(status="SUBMITTED").count()
        pending_kyc = VerificationCase.objects.filter(status="PENDING").count()
        open_reports = Report.objects.filter(status="OPEN").count()

        # Financial Stats (Sum of successful credit purchases)
        credits_sold = CreditTransaction.objects.filter(
            transaction_type="PURCHASE", status="COMPLETED"
        ).aggregate(total=Sum("amount"))["total"] or 0
        
        total_unlocks = ContactUnlock.objects.count()

        # Recent Activity
        recent_users = list(User.objects.order_by("-date_joined")[:5].values("email", "date_joined"))
        recent_listings = list(Listing.objects.order_by("-created_at")[:5].values("title", "price", "currency", "created_at"))

        return Response({
            "stats": {
                "total_users": total_users,
                "active_listings": total_active_listings,
                "credits_sold": credits_sold,
                "total_unlocks": total_unlocks,
            },
            "alerts": {
                "pending_listings": pending_listings,
                "pending_kyc": pending_kyc,
                "open_reports": open_reports,
            },
            "recent_users": recent_users,
            "recent_listings": recent_listings,
        })
'''
    CORE_VIEWS.write_text(text, encoding="utf-8")
    print("Patched apps/core/views.py: added AdminDashboardView")

# ---------------------------------------------------------------- 2. Backend URL
ACCOUNTS_URLS = ROOT / "apps" / "accounts" / "urls.py"
text = ACCOUNTS_URLS.read_text(encoding="utf-8")
if "AdminDashboardView" not in text:
    text = text.replace(
        "from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView",
        "from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView\nfrom apps.core.views import AdminDashboardView"
    )
    text = text.replace(
        'path("me/", MeView.as_view(), name="auth-me"),',
        'path("me/", MeView.as_view(), name="auth-me"),\n    path("admin-stats/", AdminDashboardView.as_view(), name="admin-stats"),'
    )
    ACCOUNTS_URLS.write_text(text, encoding="utf-8")
    print("Patched apps/accounts/urls.py: mounted AdminDashboardView")

# ---------------------------------------------------------------- 3. Frontend API
FRONTEND_API = '''
import { api } from './client'

export const adminApi = {
  getStats: () => api<any>('/auth/admin-stats/'),
}
'''
(FRONTEND / "src" / "api" / "admin.ts").write_text(FRONTEND_API.strip() + "\n", encoding="utf-8")
print("Created src/api/admin.ts")

# ---------------------------------------------------------------- 4. Frontend Page
ADMIN_PAGE = '''
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { adminApi } from '../api/admin'
import Loading from '../components/Loading'

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
  })

  if (isLoading) return <Loading />
  if (!data) return <p className="text-gray-500">Access denied or failed to load.</p>

  const { stats, alerts, recent_users, recent_listings } = data

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 min-h-[calc(100vh-200px)]">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-gray-600">Monitor NyumbaLink's growth, revenue, and moderation health.</p>
        </div>
        <Link to="/moderation" className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 font-medium shadow-sm">
          Go to Moderation Console
        </Link>
      </div>

      {/* KEY METRICS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Users</p>
          <p className="text-3xl font-bold text-gray-900">{stats.total_users}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Active Listings</p>
          <p className="text-3xl font-bold text-emerald-600">{stats.active_listings}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Credits Sold</p>
          <p className="text-3xl font-bold text-gray-900">{stats.credits_sold}</p>
        </div>
        <div className="bg-white border p-6 rounded-lg shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Contacts Unlocked</p>
          <p className="text-3xl font-bold text-gray-900">{stats.total_unlocks}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* LEFT COLUMN: NEEDS ATTENTION */}
        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Needs Attention</h2>
          <div className="space-y-4">
            <Link to="/moderation?tab=listings" className="block bg-white border-l-4 border-yellow-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Pending Listings</h3>
                <p className="text-sm text-gray-500">Listings waiting for approval</p>
              </div>
              <span className="bg-yellow-100 text-yellow-800 font-bold px-3 py-1 rounded-full">{alerts.pending_listings}</span>
            </Link>
            <Link to="/moderation?tab=kyc" className="block bg-white border-l-4 border-blue-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Pending KYC</h3>
                <p className="text-sm text-gray-500">Landlords awaiting ID verification</p>
              </div>
              <span className="bg-blue-100 text-blue-800 font-bold px-3 py-1 rounded-full">{alerts.pending_kyc}</span>
            </Link>
            <Link to="/moderation?tab=reports" className="block bg-white border-l-4 border-red-500 p-4 rounded shadow-sm hover:shadow-md transition flex justify-between items-center">
              <div>
                <h3 className="font-bold text-gray-800">Open Reports</h3>
                <p className="text-sm text-gray-500">Reported listings or users</p>
              </div>
              <span className="bg-red-100 text-red-800 font-bold px-3 py-1 rounded-full">{alerts.open_reports}</span>
            </Link>
          </div>
        </div>

        {/* RIGHT COLUMN: RECENT ACTIVITY */}
        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Recent Activity</h2>
          <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 bg-gray-50 border-b font-semibold text-sm text-gray-600">Newest Users</div>
            <ul className="divide-y">
              {recent_users.map((u: any, i: number) => (
                <li key={i} className="p-3 text-sm flex justify-between">
                  <span className="font-medium text-gray-800">{u.email}</span>
                  <span className="text-gray-400">{new Date(u.date_joined).toLocaleDateString()}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white border rounded-lg shadow-sm overflow-hidden mt-4">
            <div className="p-4 bg-gray-50 border-b font-semibold text-sm text-gray-600">Newest Listings</div>
            <ul className="divide-y">
              {recent_listings.map((l: any, i: number) => (
                <li key={i} className="p-3 text-sm flex justify-between">
                  <span className="font-medium text-gray-800 truncate max-w-[200px]">{l.title}</span>
                  <span className="text-emerald-600 font-bold">{l.currency} {Number(l.price).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "AdminDashboard.tsx").write_text(ADMIN_PAGE.strip() + "\n", encoding="utf-8")
print("Created src/pages/AdminDashboard.tsx")

# ---------------------------------------------------------------- 5. App.tsx & Layout
APP_FILE = FRONTEND / "src" / "App.tsx"
text = APP_FILE.read_text(encoding="utf-8")
if "AdminDashboard" not in text:
    text = text.replace(
        "import ModerationPage from './pages/ModerationPage'",
        "import ModerationPage from './pages/ModerationPage'\nimport AdminDashboard from './pages/AdminDashboard'"
    )
    text = text.replace(
        '<Route path="/moderation" element={<ModerationPage />} />',
        '<Route path="/moderation" element={<ModerationPage />} />\n          <Route path="/admin-dashboard" element={<AdminDashboard />} />'
    )
    APP_FILE.write_text(text, encoding="utf-8")
    print("Patched App.tsx: added AdminDashboard route")

LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"
text = LAYOUT_FILE.read_text(encoding="utf-8")
if "Admin Overview" not in text:
    old_nav = '''                {user.is_staff && <Link to="/moderation" className="text-orange-600 font-bold hover:text-orange-700">Moderation</Link>}'''
    new_nav = '''                {user.is_staff && <Link to="/admin-dashboard" className="text-purple-700 font-bold hover:text-purple-800">Admin Overview</Link>}
                {user.is_staff && <Link to="/moderation" className="text-orange-600 font-bold hover:text-orange-700">Moderation</Link>}'''
    text = text.replace(old_nav, new_nav)
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("Patched Layout.tsx: added Admin Overview link")

print("""
Phase 20 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as the Superuser (howardmupeta@nyumbalink.com).
  3. You will see a purple "Admin Overview" link in the top navigation.
  4. Click it to see the entire platform's health:
     - Total users, active listings, credits sold.
     - A "Needs Attention" panel with direct links to the specific moderation tabs.
     - A live feed of the newest users and listings on NyumbaLink.
""")