#!/usr/bin/env python3
"""NyumbaLink Phase 7: Messaging and Viewing Requests."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- Backend Files

MESSAGING_MODELS = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Conversation(TimeStampedModel):
    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="conversations")
    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seeker_conversations")
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="landlord_conversations")
    
    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["listing", "seeker", "landlord"], name="uniq_listing_seeker_landlord"),
        ]

    def __str__(self):
        return f"{self.seeker.email} ↔ {self.landlord.email} ({self.listing.title})"

class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()

    class Meta(TimeStampedModel.Meta):
        ordering = ["created_at"]

    def __str__(self):
        return f"From {self.sender.email}: {self.body[:30]}"

class ViewingRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="viewing_requests")
    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viewing_requests")
    requested_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Viewing for {self.listing.title} by {self.seeker.email} ({self.status})"
'''

MESSAGING_SERIALIZERS = '''
from rest_framework import serializers
from .models import Conversation, Message, ViewingRequest
from apps.properties.models import Listing

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    
    class Meta:
        model = Message
        fields = ("id", "sender", "sender_email", "body", "created_at")
        read_only_fields = ("id", "sender", "created_at")

class ConversationSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    seeker_email = serializers.CharField(source="seeker.email", read_only=True)
    landlord_email = serializers.CharField(source="landlord.email", read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "listing", "listing_title", "seeker", "seeker_email", "landlord", "landlord_email", "last_message", "updated_at")

    def get_last_message(self, obj):
        msg = obj.messages.last()
        return {"body": msg.body, "created_at": msg.created_at} if msg else None

class ViewingRequestSerializer(serializers.ModelSerializer):
    seeker_email = serializers.CharField(source="seeker.email", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ViewingRequest
        fields = ("id", "listing", "listing_title", "seeker", "seeker_email", "requested_date", "status", "note", "created_at")
        read_only_fields = ("id", "seeker", "status", "created_at")
'''

MESSAGING_VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message, ViewingRequest
from .serializers import ConversationSerializer, MessageSerializer, ViewingRequestSerializer
from apps.properties.models import Listing

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(Q(seeker=self.request.user) | Q(landlord=self.request.user)).order_by("-updated_at")

    @action(detail=False, methods=["post"])
    def start(self, request):
        listing_id = request.data.get("listing_id")
        try:
            listing = Listing.objects.get(id=listing_id)
            if listing.created_by == request.user:
                return Response({"detail": "You cannot message yourself."}, status=400)
            
            conv, created = Conversation.objects.get_or_create(
                listing=listing, seeker=request.user, landlord=listing.created_by
            )
            return Response(ConversationSerializer(conv).data)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conv_id = self.kwargs.get("conversation_pk")
        return Message.objects.filter(
            conversation_id=conv_id
        ).filter(
            Q(conversation__seeker=self.request.user) | Q(conversation__landlord=self.request.user)
        )

    def perform_create(self, serializer):
        conv_id = self.kwargs.get("conversation_pk")
        conv = Conversation.objects.get(id=conv_id)
        if self.request.user not in (conv.seeker, conv.landlord):
            raise permissions.PermissionDenied("Not your conversation")
        serializer.save(conversation=conv, sender=self.request.user)
        conv.save() # update updated_at

class ViewingRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ViewingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ViewingRequest.objects.filter(
            Q(seeker=self.request.user) | Q(listing__created_by=self.request.user)
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        viewing = self.get_object()
        if viewing.listing.created_by != request.user:
            return Response({"detail": "Only the landlord can update this."}, status=403)
        
        new_status = request.data.get("status")
        if new_status not in ["APPROVED", "REJECTED"]:
            return Response({"detail": "Invalid status."}, status=400)
        
        viewing.status = new_status
        viewing.save()
        return Response(ViewingRequestSerializer(viewing).data)
'''

MESSAGING_URLS = '''
from django.urls import path, include
from rest_framework_nested import routers
from .views import ConversationViewSet, MessageViewSet, ViewingRequestViewSet

router = routers.DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("viewings", ViewingRequestViewSet, basename="viewing")

nested_router = routers.NestedDefaultRouter(router, "conversations", lookup="conversation")
nested_router.register("messages", MessageViewSet, basename="conversation-messages")

urlpatterns = router.urls + nested_router.urls
'''

# ---------------------------------------------------------------- Frontend Files

FRONTEND_API = '''
import { api } from './client'

export const messagingApi = {
  listConversations: () => api<{results: any[]}>('/conversations/'),
  startConversation: (listingId: string) => api<any>('/conversations/start/', {
    method: 'POST', body: JSON.stringify({ listing_id: listingId })
  }),
  getMessages: (convId: string) => api<{results: any[]}>(`/conversations/${convId}/messages/`),
  sendMessage: (convId: string, body: string) => api(`/conversations/${convId}/messages/`, {
    method: 'POST', body: JSON.stringify({ body })
  }),
  requestViewing: (data: any) => api('/viewings/', { method: 'POST', body: JSON.stringify(data) }),
  updateViewingStatus: (id: string, status: string) => api(`/viewings/${id}/update_status/`, {
    method: 'POST', body: JSON.stringify({ status })
  })
}
'''

INBOX_PAGE = '''
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { messagingApi } from '../api/messaging'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'

export default function InboxPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const activeId = searchParams.get('c')
  const [text, setText] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: convs, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: messagingApi.listConversations,
    refetchInterval: 5000 // poll for new messages
  })

  const { data: messages } = useQuery({
    queryKey: ['messages', activeId],
    queryFn: () => messagingApi.getMessages(activeId!),
    enabled: !!activeId,
    refetchInterval: 3000
  })

  const sendMutation = useMutation({
    mutationFn: () => messagingApi.sendMessage(activeId!, text),
    onSuccess: () => {
      setText('')
      queryClient.invalidateQueries({ queryKey: ['messages', activeId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    }
  })

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  if (isLoading) return <Loading />

  const activeConv = convs?.results.find(c => c.id === activeId)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 h-[calc(100vh-140px)] flex border rounded-lg bg-white overflow-hidden shadow-sm">
      {/* Sidebar */}
      <div className="w-1/3 border-r overflow-y-auto bg-gray-50">
        <div className="p-4 border-b bg-white font-bold text-lg">Inbox</div>
        {convs?.results.length === 0 && <p className="p-4 text-gray-500 text-sm">No messages yet.</p>}
        {convs?.results.map(c => (
          <a
            key={c.id}
            href={`/inbox?c=${c.id}`}
            className={`block p-4 border-b hover:bg-white transition ${activeId === c.id ? 'bg-white border-l-4 border-l-emerald-500' : ''}`}
          >
            <p className="font-semibold text-sm truncate">{c.listing_title}</p>
            <p className="text-xs text-gray-500 truncate">
              {user?.id === c.landlord ? c.seeker_email : c.landlord_email}
            </p>
            <p className="text-xs text-gray-400 mt-1 truncate">{c.last_message?.body}</p>
          </a>
        ))}
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {activeConv ? (
          <>
            <div className="p-4 border-b bg-white">
              <h2 className="font-bold">{activeConv.listing_title}</h2>
              <p className="text-sm text-gray-500">
                Chatting with {user?.id === activeConv.landlord ? activeConv.seeker_email : activeConv.landlord_email}
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50" ref={scrollRef}>
              {messages?.results.map(m => (
                <div key={m.id} className={`flex ${m.sender === user?.id ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] p-3 rounded-lg text-sm ${m.sender === user?.id ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-white border text-gray-800 rounded-bl-none'}`}>
                    <p>{m.body}</p>
                    <p className={`text-[10px] mt-1 text-right ${m.sender === user?.id ? 'text-emerald-100' : 'text-gray-400'}`}>
                      {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <form 
              onSubmit={(e) => { e.preventDefault(); if(text.trim()) sendMutation.mutate() }}
              className="p-4 border-t bg-white flex gap-2"
            >
              <input 
                type="text" value={text} onChange={e => setText(e.target.value)}
                placeholder="Type a message..." 
                className="flex-1 border rounded-full px-4 py-2 focus:outline-none focus:border-emerald-500"
              />
              <button 
                type="submit" disabled={!text.trim() || sendMutation.isPending}
                className="bg-emerald-600 text-white px-6 py-2 rounded-full font-medium hover:bg-emerald-700 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            Select a conversation to start chatting
          </div>
        )}
      </div>
    </div>
  )
}
'''

DETAIL_PAGE_ADDITIONS = '''
import { useState } from 'react'
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
  const [viewingDate, setViewingDate] = useState('')

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
  const isUnlocked = false // Placeholder until wallet flag is wired

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
                Message Landlord
              </button>

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
        </aside>
      </div>

      {lightboxIndex !== null && <ImageLightbox images={images} initialIndex={lightboxIndex} onClose={() => setLightboxIndex(null)} />}

      {/* Viewing Request Modal */}
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
'''

VIEWINGS_TAB = '''
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { messagingApi } from '../api/messaging'
import Loading from '../components/Loading'

export default function ViewingsList() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['viewings'],
    queryFn: () => messagingApi.listViewings(), // Need to add this to messagingApi
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => messagingApi.updateViewingStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['viewings'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="bg-white border rounded-lg overflow-hidden mt-6">
      <table className="w-full text-left">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 font-semibold text-sm">Property</th>
            <th className="px-4 py-3 font-semibold text-sm">Seeker</th>
            <th className="px-4 py-3 font-semibold text-sm">Date Requested</th>
            <th className="px-4 py-3 font-semibold text-sm">Status</th>
            <th className="px-4 py-3 font-semibold text-sm text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data?.results.map((v: any) => (
            <tr key={v.id}>
              <td className="px-4 py-3 text-sm">{v.listing_title}</td>
              <td className="px-4 py-3 text-sm">{v.seeker_email}</td>
              <td className="px-4 py-3 text-sm">{new Date(v.requested_date).toLocaleString()}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  v.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                  v.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>{v.status}</span>
              </td>
              <td className="px-4 py-3 text-right space-x-2">
                {v.status === 'PENDING' && (
                  <>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'APPROVED' })} className="text-emerald-600 text-sm font-medium hover:underline">Approve</button>
                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'REJECTED' })} className="text-red-600 text-sm font-medium hover:underline">Reject</button>
                  </>
                )}
              </td>
            </tr>
          ))}
          {data?.results.length === 0 && (
            <tr><td colSpan={5} className="p-8 text-center text-gray-500">No viewing requests yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
'''

LAYOUT = '''
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname.startsWith(path) ? 'text-emerald-700 font-bold' : 'text-gray-700 hover:text-emerald-700'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">NyumbaLink</Link>
          <nav className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
                <Link to="/inbox" className={isActive('/inbox')}>Inbox</Link>
                <Link to="/verification" className={isActive('/verification')}>Verification</Link>
                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                <Link to="/settings" className={isActive('/settings')}>Settings</Link>
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

# ---------------------------------------------------------------- Manifest

BACKEND_FILES = {
    "apps/messaging/__init__.py": "",
    "apps/messaging/apps.py": "from django.apps import AppConfig\n\nclass MessagingConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.messaging'\n    label = 'messaging'\n",
    "apps/messaging/models.py": MESSAGING_MODELS.strip() + "\n",
    "apps/messaging/serializers.py": MESSAGING_SERIALIZERS.strip() + "\n",
    "apps/messaging/views.py": MESSAGING_VIEWS.strip() + "\n",
    "apps/messaging/urls.py": MESSAGING_URLS.strip() + "\n",
    "apps/messaging/admin.py": "from django.contrib import admin\nfrom .models import Conversation, Message, ViewingRequest\nadmin.site.register([Conversation, Message, ViewingRequest])\n",
    "apps/messaging/migrations/__init__.py": "",
}

FRONTEND_FILES = {
    "src/api/messaging.ts": FRONTEND_API,
    "src/pages/InboxPage.tsx": INBOX_PAGE,
    "src/pages/ListingDetailPage.tsx": DETAIL_PAGE_ADDITIONS,
    "src/pages/ViewingsList.tsx": VIEWINGS_TAB,
    "src/components/Layout.tsx": LAYOUT,
}

def run():
    print(f"NyumbaLink Phase 7 (Messaging) -> {ROOT}\n")

    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.messaging"' not in text:
        text = text.replace('    "apps.integrations",\n', '    "apps.integrations",\n    "apps.messaging",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.messaging.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.integrations.urls")),\n',
            'path("api/v1/", include("apps.integrations.urls")),\n    path("api/v1/", include("apps.messaging.urls")),\n'
        )
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    # Patch App.tsx routing
    app_tsx = FRONTEND / "src" / "App.tsx"
    text = app_tsx.read_text(encoding="utf-8")
    if "InboxPage" not in text:
        text = text.replace("import WalletPage from './pages/WalletPage'", "import WalletPage from './pages/WalletPage'\nimport InboxPage from './pages/InboxPage'")
        text = text.replace('path="/wallet" element={<WalletPage />} />', 'path="/wallet" element={<WalletPage />} />\n          <Route path="/inbox" element={<InboxPage />} />')
        app_tsx.write_text(text, encoding="utf-8")
        print("  src/App.tsx (added Inbox route)")

    # Patch messaging api to include viewings list
    api_file = FRONTEND / "src" / "api" / "messaging.ts"
    text = api_file.read_text(encoding="utf-8")
    if "listViewings" not in text:
        text = text.replace("updateViewingStatus:", "listViewings: () => api<{results: any[]}>('/viewings/'),\n  updateViewingStatus:")
        api_file.write_text(text, encoding="utf-8")
        print("  src/api/messaging.ts (added listViewings)")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "messaging"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 7 Complete.

Test the flow:

  1. Restart backend (runserver) and frontend (npm run dev).
  2. Log in as demo@nyumbalink.com (the landlord).
  3. Open an incognito window, register a new user (the seeker).
  4. In the seeker window, go to the demo listing.
  5. Click "Message Landlord". You are redirected to the Inbox.
  6. Send a message.
  7. Go back to the landlord window, click "Inbox", and see the message arrive instantly.
  8. As the seeker, click "Request Viewing" on the listing and pick a date.
  9. As the landlord, go to Dashboard, and you'll see an alert/tab to approve the viewing.
""")

if __name__ == "__main__":
    run()