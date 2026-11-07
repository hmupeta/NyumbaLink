#!/usr/bin/env python3
"""NyumbaLink Phase 7b: WhatsApp-style Chat (Replies, Reactions, Read Receipts)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Models

MODELS = '''
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
    
    # WhatsApp Features
    is_read = models.BooleanField(default=False)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")

    class Meta(TimeStampedModel.Meta):
        ordering = ["created_at"]

    def __str__(self):
        return f"From {self.sender.email}: {self.body[:30]}"

class MessageReaction(TimeStampedModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="uniq_message_user_reaction"),
        ]

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

SERIALIZERS = '''
from rest_framework import serializers
from .models import Conversation, Message, ViewingRequest, MessageReaction

class MessageReactionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    class Meta:
        model = MessageReaction
        fields = ("id", "user", "user_email", "emoji")

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    reply_to_text = serializers.CharField(source="reply_to.body", read_only=True)
    reply_to_sender = serializers.CharField(source="reply_to.sender.email", read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Message
        fields = ("id", "sender", "sender_email", "body", "created_at", "is_read", "reply_to", "reply_to_text", "reply_to_sender", "reactions")
        read_only_fields = ("id", "sender", "created_at", "is_read")

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

VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message, ViewingRequest, MessageReaction
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
        qs = Message.objects.filter(conversation_id=conv_id).filter(
            Q(conversation__seeker=self.request.user) | Q(conversation__landlord=self.request.user)
        ).select_related("reply_to", "sender").prefetch_related("reactions")

        # Mark messages as read if I am NOT the sender
        Message.objects.filter(conversation_id=conv_id, is_read=False).exclude(sender=self.request.user).update(is_read=True)
        return qs

    def perform_create(self, serializer):
        conv_id = self.kwargs.get("conversation_pk")
        conv = Conversation.objects.get(id=conv_id)
        if self.request.user not in (conv.seeker, conv.landlord):
            raise permissions.PermissionDenied("Not your conversation")
        serializer.save(conversation=conv, sender=self.request.user)
        conv.save() # update updated_at

    @action(detail=True, methods=["post"])
    def react(self, request, conversation_pk=None, pk=None):
        message = self.get_object()
        emoji = request.data.get("emoji")
        
        # Toggle reaction
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, defaults={"emoji": emoji}
        )
        if not created:
            if reaction.emoji == emoji:
                reaction.delete()
                return Response({"status": "removed"})
            else:
                reaction.emoji = emoji
                reaction.save()
        return Response({"status": "added", "emoji": emoji})
'''

# ---------------------------------------------------------------- 2. Frontend UI

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
  const [replyTo, setReplyTo] = useState<any>(null)
  const [showEmojiFor, setShowEmojiFor] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: convs, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: messagingApi.listConversations,
    refetchInterval: 5000
  })

  const { data: messages } = useQuery({
    queryKey: ['messages', activeId],
    queryFn: () => messagingApi.getMessages(activeId!),
    enabled: !!activeId,
    refetchInterval: 3000 // Poll every 3s for read receipts and new messages
  })

  const sendMutation = useMutation({
    mutationFn: () => messagingApi.sendMessage(activeId!, text, replyTo?.id),
    onSuccess: () => {
      setText('')
      setReplyTo(null)
      queryClient.invalidateQueries({ queryKey: ['messages', activeId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    }
  })

  const reactMutation = useMutation({
    mutationFn: ({ msgId, emoji }: { msgId: string, emoji: string }) => 
      messagingApi.reactToMessage(activeId!, msgId, emoji),
    onSuccess: () => {
      setShowEmojiFor(null)
      queryClient.invalidateQueries({ queryKey: ['messages', activeId] })
    }
  })

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  if (isLoading) return <Loading />

  const activeConv = convs?.results.find(c => c.id === activeId)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 h-[calc(100vh-140px)] flex border rounded-lg bg-white overflow-hidden shadow-sm">
      {/* Sidebar */}
      <div className="w-1/3 border-r overflow-y-auto bg-gray-50 flex flex-col">
        <div className="p-4 border-b bg-white font-bold text-lg">Inbox</div>
        <div className="flex-1">
          {convs?.results.map(c => (
            <a key={c.id} href={`/inbox?c=${c.id}`} className={`block p-4 border-b hover:bg-white transition ${activeId === c.id ? 'bg-white border-l-4 border-l-emerald-500' : ''}`}>
              <p className="font-semibold text-sm truncate">{c.listing_title}</p>
              <p className="text-xs text-gray-500 truncate">{user?.id === c.landlord ? c.seeker_email : c.landlord_email}</p>
              <p className="text-xs text-gray-400 mt-1 truncate">{c.last_message?.body}</p>
            </a>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {activeConv ? (
          <>
            <div className="p-4 border-b bg-white">
              <h2 className="font-bold">{activeConv.listing_title}</h2>
              <p className="text-sm text-gray-500">Chatting with {user?.id === activeConv.landlord ? activeConv.seeker_email : activeConv.landlord_email}</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50" ref={scrollRef}>
              {messages?.results.map(m => {
                const isMine = m.sender === user?.id
                return (
                  <div key={m.id} className={`flex flex-col ${isMine ? 'items-end' : 'items-start'} group relative`}>
                    
                    {/* Message Bubble */}
                    <div className={`relative max-w-[75%] p-3 rounded-lg text-sm shadow-sm ${isMine ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-white border text-gray-800 rounded-bl-none'}`}>
                      
                      {/* Reply Quote Block */}
                      {m.reply_to_text && (
                        <div className={`mb-2 p-2 rounded text-xs border-l-4 ${isMine ? 'bg-emerald-700/50 border-emerald-300 text-emerald-50' : 'bg-gray-100 border-gray-400 text-gray-600'}`}>
                          <p className="font-semibold mb-1">{m.reply_to_sender}</p>
                          <p className="truncate">{m.reply_to_text}</p>
                        </div>
                      )}

                      <p>{m.body}</p>
                      
                      {/* Time & Ticks */}
                      <div className={`flex items-center justify-end gap-1 mt-1 text-[10px] ${isMine ? 'text-emerald-100' : 'text-gray-400'}`}>
                        <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        {isMine && (
                          <span className="ml-1">
                            {m.is_read ? (
                              <span className="text-blue-300 text-xs">✓✓</span> // Blue double tick
                            ) : (
                              <span className="text-emerald-200 text-xs">✓</span> // Single tick
                            )}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Reactions Display */}
                    {m.reactions.length > 0 && (
                      <div className={`flex gap-1 mt-1 z-10 ${isMine ? 'mr-2' : 'ml-2'}`}>
                        {m.reactions.map((r: any) => (
                          <span key={r.id} className="bg-white border rounded-full px-1.5 py-0.5 text-xs shadow-sm">
                            {r.emoji}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Hover Actions (Reply & React) */}
                    <div className={`absolute top-0 -mt-3 opacity-0 group-hover:opacity-100 transition flex gap-1 ${isMine ? '-left-20' : '-right-20'}`}>
                      <button onClick={() => setReplyTo(m)} className="bg-white border p-1.5 rounded-full shadow hover:bg-gray-50 text-gray-500">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 17 4 12 9 7"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H4"></path></svg>
                      </button>
                      <button onClick={() => setShowEmojiFor(m.id)} className="bg-white border p-1.5 rounded-full shadow hover:bg-gray-50 text-gray-500">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>
                      </button>
                    </div>

                    {/* Emoji Picker */}
                    {showEmojiFor === m.id && (
                      <div className={`absolute top-8 z-20 bg-white border shadow-lg rounded-full px-2 py-1 flex gap-2 ${isMine ? 'right-0' : 'left-0'}`}>
                        {['👍', '❤️', '😂', '😮', '😢', '🙏'].map(emoji => (
                          <button key={emoji} onClick={() => reactMutation.mutate({ msgId: m.id, emoji })} className="hover:scale-125 transition text-lg">
                            {emoji}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Input Area with Reply context */}
            <div className="border-t bg-white">
              {replyTo && (
                <div className="p-2 bg-gray-50 border-b flex justify-between items-center px-4">
                  <div className="border-l-4 border-emerald-500 pl-2 text-sm text-gray-600">
                    <span className="font-bold text-xs block">Replying to {replyTo.sender_email}</span>
                    <span className="truncate block max-w-lg">{replyTo.body}</span>
                  </div>
                  <button onClick={() => setReplyTo(null)} className="text-gray-400 hover:text-red-500">✕</button>
                </div>
              )}
              <form onSubmit={(e) => { e.preventDefault(); if(text.trim()) sendMutation.mutate() }} className="p-4 flex gap-2">
                <input 
                  type="text" value={text} onChange={e => setText(e.target.value)}
                  placeholder="Type a message..." 
                  className="flex-1 border rounded-full px-4 py-2 focus:outline-none focus:border-emerald-500 bg-gray-50"
                />
                <button type="submit" disabled={!text.trim() || sendMutation.isPending} className="bg-emerald-600 text-white px-6 py-2 rounded-full font-medium hover:bg-emerald-700 disabled:opacity-50">
                  Send
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">Select a conversation</div>
        )}
      </div>
    </div>
  )
}
'''

API_FILE = '''
import { api } from './client'

export const messagingApi = {
  listConversations: () => api<{results: any[]}>('/conversations/'),
  startConversation: (listingId: string) => api<any>('/conversations/start/', {
    method: 'POST', body: JSON.stringify({ listing_id: listingId })
  }),
  getMessages: (convId: string) => api<{results: any[]}>(`/conversations/${convId}/messages/`),
  
  sendMessage: (convId: string, body: string, replyToId?: string) => api(`/conversations/${convId}/messages/`, {
    method: 'POST', 
    body: JSON.stringify({ body, reply_to: replyToId || null })
  }),
  
  reactToMessage: (convId: string, msgId: string, emoji: string) => api(`/conversations/${convId}/messages/${msgId}/react/`, {
    method: 'POST', body: JSON.stringify({ emoji })
  }),

  requestViewing: (data: any) => api('/viewings/', { method: 'POST', body: JSON.stringify(data) }),
  listViewings: () => api<{results: any[]}>('/viewings/'),
  updateViewingStatus: (id: string, status: string) => api(`/viewings/${id}/update_status/`, {
    method: 'POST', body: JSON.stringify({ status })
  })
}
'''

def run():
    print("Upgrading chat to WhatsApp-style...")
    
    # 1. Update Models
    (ROOT / "apps" / "messaging" / "models.py").write_text(MODELS.strip() + "\n", encoding="utf-8")
    # 2. Update Serializers
    (ROOT / "apps" / "messaging" / "serializers.py").write_text(SERIALIZERS.strip() + "\n", encoding="utf-8")
    # 3. Update Views
    (ROOT / "apps" / "messaging" / "views.py").write_text(VIEWS.strip() + "\n", encoding="utf-8")
    # 4. Update Frontend API
    (FRONTEND / "src" / "api" / "messaging.ts").write_text(API_FILE.strip() + "\n", encoding="utf-8")
    # 5. Update Frontend Inbox
    (FRONTEND / "src" / "pages" / "InboxPage.tsx").write_text(INBOX_PAGE.strip() + "\n", encoding="utf-8")

    print("Applying migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "messaging"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Done! Restart your backend and frontend.

Test it:
  1. Open two browser windows (one for landlord, one for seeker).
  2. Send a message from the seeker.
  3. Notice the single tick (✓) next to the message.
  4. Switch to the landlord window. The message appears, and when the landlord's window polls, the tick turns blue (✓✓).
  5. Hover over a message to see the Reply and Emoji buttons.
  6. Click Reply, type a message, and send. You will see the quoted block.
  7. Click the Emoji button and react with a 👍 or ❤️. It will pop up under the message.
""")

if __name__ == "__main__":
    run()