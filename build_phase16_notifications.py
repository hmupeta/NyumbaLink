#!/usr/bin/env python3
"""NyumbaLink Phase 16: In-App Notifications."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Files

NOTIFICATION_MODEL = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Notification(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=128)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, help_text="Frontend URL to redirect to")
    is_read = models.BooleanField(default=False)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
'''

NOTIFICATION_SERVICES = '''
from .models import Notification

def create_notification(user, title, message, link=""):
    if user:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            link=link
        )
'''

NOTIFICATION_SIGNALS = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.messaging.models import Message, ViewingRequest
from apps.reviews.models import Review
from .services import create_notification

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        conv = instance.conversation
        # Notify the receiver
        receiver = conv.landlord if instance.sender == conv.seeker else conv.seeker
        create_notification(
            user=receiver,
            title=f"New message from {instance.sender.first_name or instance.sender.email}",
            message=instance.body[:50] + ("..." if len(instance.body) > 50 else ""),
            link=f"/inbox?c={conv.id}"
        )

@receiver(post_save, sender=ViewingRequest)
def notify_viewing_request(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.listing.created_by,
            title="New Viewing Request",
            message=f"{instance.seeker.email} requested to view {instance.listing.title}",
            link=f"/dashboard"
        )
    else:
        # If status was updated (e.g., APPROVED/REJECTED)
        if instance.status != "PENDING":
            create_notification(
                user=instance.seeker,
                title=f"Viewing Request {instance.status}",
                message=f"Your request to view {instance.listing.title} was {instance.status.lower()}.",
                link=f"/listings/{instance.listing.id}"
            )

@receiver(post_save, sender=Review)
def notify_new_review(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.landlord,
            title="New Review Received",
            message=f"You received a {instance.rating}-star review.",
            link=f"/profiles/{instance.landlord.id}"
        )
'''

NOTIFICATION_SERIALIZERS = '''
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "link", "is_read", "created_at")
'''

NOTIFICATION_VIEWS = '''
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"count": count})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"status": "ok"})
'''

NOTIFICATION_URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
urlpatterns = router.urls
'''

BACKEND_FILES = {
    "apps/notifications/__init__.py": "",
    "apps/notifications/apps.py": "from django.apps import AppConfig\n\nclass NotificationsConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.notifications'\n    label = 'notifications'\n\n    def ready(self):\n        import apps.notifications.signals",
    "apps/notifications/models.py": NOTIFICATION_MODEL.strip() + "\n",
    "apps/notifications/services.py": NOTIFICATION_SERVICES.strip() + "\n",
    "apps/notifications/signals.py": NOTIFICATION_SIGNALS.strip() + "\n",
    "apps/notifications/serializers.py": NOTIFICATION_SERIALIZERS.strip() + "\n",
    "apps/notifications/views.py": NOTIFICATION_VIEWS.strip() + "\n",
    "apps/notifications/urls.py": NOTIFICATION_URLS.strip() + "\n",
    "apps/notifications/admin.py": "from django.contrib import admin\nfrom .models import Notification\nadmin.site.register(Notification)\n",
    "apps/notifications/migrations/__init__.py": "",
}

# ---------------------------------------------------------------- 2. Frontend API
FRONTEND_API = '''
import { api } from './client'

export const notificationsApi = {
  list: () => api<{results: any[]}>('/notifications/'),
  unreadCount: () => api<{count: number}>('/notifications/unread_count/'),
  markRead: (id: string) => api(`/notifications/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ is_read: true })
  }),
  markAllRead: () => api('/notifications/mark_all_read/', { method: 'POST' })
}
'''

# ---------------------------------------------------------------- 3. Frontend Bell Component
BELL_COMPONENT = '''
import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/notifications'

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 10000 // Poll every 10s
  })

  const { data: listData } = useQuery({
    queryKey: ['notifications-list'],
    queryFn: notificationsApi.list,
    enabled: isOpen,
  })

  const markAllMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
    }
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const unreadCount = unreadData?.count || 0

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-emerald-700 transition focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform translate-x-1/4 -translate-y-1/4 bg-red-600 rounded-full">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-100 z-50 overflow-hidden">
          <div className="flex justify-between items-center px-4 py-3 bg-gray-50 border-b">
            <h3 className="font-bold text-gray-800 text-sm">Notifications</h3>
            {unreadCount > 0 && (
              <button onClick={() => markAllMutation.mutate()} className="text-xs text-emerald-600 hover:underline">
                Mark all read
              </button>
            )}
          </div>
          
          <div className="max-h-96 overflow-y-auto">
            {!listData?.results || listData.results.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">No notifications yet.</div>
            ) : (
              listData.results.map((n: any) => (
                <Link 
                  key={n.id} 
                  to={n.link || "#"}
                  onClick={() => {
                    if (!n.is_read) {
                      notificationsApi.markRead(n.id)
                      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
                    }
                    setIsOpen(false)
                  }}
                  className={`block px-4 py-3 border-b hover:bg-gray-50 transition ${!n.is_read ? 'bg-emerald-50/50' : ''}`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <p className={`text-sm ${!n.is_read ? 'font-bold text-gray-900' : 'font-medium text-gray-700'}`}>{n.title}</p>
                    <span className="text-[10px] text-gray-400 whitespace-nowrap ml-2">
                      {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2">{n.message}</p>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
'''

LAYOUT = '''
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path ? 'text-emerald-700 font-bold' : 'text-gray-700 hover:text-emerald-700'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 font-sans">
      
      <header className="border-b bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700 tracking-tight">NyumbaLink</Link>
          <nav className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
                <Link to="/saved" className={isActive('/saved')}>Saved</Link>
                <Link to="/inbox" className={isActive('/inbox')}>Inbox</Link>
                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                <NotificationBell />
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline font-medium">{user.email}</span>
                <button onClick={() => { logout(); navigate('/') }} className="text-red-600 hover:underline font-medium">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700 font-medium">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-4 py-1.5 rounded-md hover:bg-emerald-700 font-medium transition">Register</Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1"><Outlet /></main>

      <footer className="bg-slate-900 text-slate-300 pt-16 pb-8 border-t border-slate-800 mt-auto">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-12">
            <div>
              <Link to="/" className="text-2xl font-bold text-white tracking-tight block mb-4">NyumbaLink</Link>
              <p className="text-sm text-slate-400 mb-6 leading-relaxed">Find your place. Connect your world. The most trusted property marketplace in Zambia.</p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Explore</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/?type=rent" className="hover:text-emerald-400 transition">Rent a Home</Link></li>
                <li><Link to="/?type=sale" className="hover:text-emerald-400 transition">Buy a Home</Link></li>
                <li><Link to="/" className="hover:text-emerald-400 transition">All Listings</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">For Landlords</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/dashboard/listings/new" className="hover:text-emerald-400 transition">List a Property</Link></li>
                <li><Link to="/verification" className="hover:text-emerald-400 transition">Get Verified</Link></li>
                <li><Link to="/wallet" className="hover:text-emerald-400 transition">Pricing & Plans</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Support</h4>
              <ul className="space-y-3 text-sm mb-6">
                <li><a href="#" className="hover:text-emerald-400 transition">Help Centre</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition">Contact Us</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-500">
            <div className="flex gap-4">
              <a href="#" className="hover:text-white transition">Terms of Use</a>
              <a href="#" className="hover:text-white transition">Privacy Policy</a>
            </div>
            <p>© {new Date().getFullYear()} NyumbaLink. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
'''

# ---------------------------------------------------------------- 4. Execution

FRONTEND_FILES = {
    "src/api/notifications.ts": FRONTEND_API,
    "src/components/NotificationBell.tsx": BELL_COMPONENT,
    "src/components/Layout.tsx": LAYOUT,
}

def run():
    print(f"NyumbaLink Phase 16 (Notifications) -> {ROOT}\n")

    print("Writing backend files:")
    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nPatching settings and urls:")
    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.notifications"' not in text:
        text = text.replace('    "apps.reviews",\n', '    "apps.reviews",\n    "apps.notifications",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.notifications.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.reviews.urls")),\n',
            'path("api/v1/", include("apps.reviews.urls")),\n    path("api/v1/", include("apps.notifications.urls")),\n'
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
    subprocess.run([sys.executable, "manage.py", "makemigrations", "notifications"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 16 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Open two browser windows: one as the Landlord (demo@nyumbalink.com) and one as a Seeker (seeker@nyumbalink.com).
  3. In the Seeker window, send a message to the Landlord or request a viewing.
  4. Look at the Landlord's window: within 10 seconds, the Bell icon in the header will show a red badge!
  5. Click the Bell to see the dropdown notification.
  6. Click the notification. It will take you directly to the chat, and the notification will be marked as read (the badge will disappear).
""")

if __name__ == "__main__":
    run()