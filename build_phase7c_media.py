#!/usr/bin/env python3
"""NyumbaLink Phase 7c: Voice Notes and Media Sharing."""
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
    class MessageType(models.TextChoices):
        TEXT = "TEXT", "Text"
        IMAGE = "IMAGE", "Image"
        AUDIO = "AUDIO", "Audio"
        FILE = "FILE", "File"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    
    # Media fields
    message_type = models.CharField(max_length=16, choices=MessageType.choices, default=MessageType.TEXT)
    file = models.FileField(upload_to="chat_files/", null=True, blank=True)

    # WhatsApp Features
    is_read = models.BooleanField(default=False)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")

    class Meta(TimeStampedModel.Meta):
        ordering = ["created_at"]

    def __str__(self):
        return f"From {self.sender.email}: {self.message_type}"

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
    class Meta:
        model = MessageReaction
        fields = ("id", "user", "emoji")

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    reply_to_text = serializers.SerializerMethodField()
    reply_to_sender = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ("id", "sender", "sender_email", "body", "message_type", "file", "file_url", "created_at", "is_read", "reply_to", "reply_to_text", "reply_to_sender", "reactions")
        read_only_fields = ("id", "sender", "created_at", "is_read")
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_reply_to_text(self, obj):
        if obj.reply_to:
            return obj.reply_to.body or f"[{obj.reply_to.message_type}]"
        return None

    def get_reply_to_sender(self, obj):
        if obj.reply_to:
            return obj.reply_to.sender.email
        return None

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
        if not msg: return None
        return {"body": msg.body or f"[{msg.message_type}]", "created_at": msg.created_at}

class ViewingRequestSerializer(serializers.ModelSerializer):
    seeker_email = serializers.CharField(source="seeker.email", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ViewingRequest
        fields = ("id", "listing", "listing_title", "seeker", "seeker_email", "requested_date", "status", "note", "created_at")
        read_only_fields = ("id", "seeker", "status", "created_at")
'''

# ---------------------------------------------------------------- 2. Frontend UI (Inbox with Media)
INBOX_PAGE = '''
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { messagingApi } from '../api/messaging'
import { getMediaUrl } from '../api/listings'
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
  const [isRecording, setIsRecording] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const { data: convs, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: messagingApi.listConversations,
    refetchInterval: 5000
  })

  const { data: messages } = useQuery({
    queryKey: ['messages', activeId],
    queryFn: () => messagingApi.getMessages(activeId!),
    enabled: !!activeId,
    refetchInterval: 3000 
  })

  const sendMutation = useMutation({
    mutationFn: (data: { text?: string, file?: File, type: string }) => 
      messagingApi.sendMessage(activeId!, data.text || '', replyTo?.id, data.file, data.type),
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

  // --- Voice Recording Logic ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const file = new File([audioBlob], 'voice-note.webm', { type: 'audio/webm' })
        sendMutation.mutate({ file, type: 'AUDIO' })
        stream.getTracks().forEach(track => track.stop()) // cleanup mic
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      alert('Microphone access denied or not available.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const isImage = file.type.startsWith('image/')
    sendMutation.mutate({ file, type: isImage ? 'IMAGE' : 'FILE' })
    e.target.value = ''
  }

  if (isLoading) return <Loading />
  const activeConv = convs?.results.find(c => c.id === activeId)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 h-[calc(100vh-140px)] flex border rounded-lg bg-white overflow-hidden shadow-sm">
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
                    
                    <div className={`relative max-w-[75%] p-3 rounded-lg text-sm shadow-sm ${isMine ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-white border text-gray-800 rounded-bl-none'}`}>
                      
                      {m.reply_to_text && (
                        <div className={`mb-2 p-2 rounded text-xs border-l-4 ${isMine ? 'bg-emerald-700/50 border-emerald-300 text-emerald-50' : 'bg-gray-100 border-gray-400 text-gray-600'}`}>
                          <p className="font-semibold mb-1">{m.reply_to_sender}</p>
                          <p className="truncate">{m.reply_to_text}</p>
                        </div>
                      )}

                      {/* Render Content based on Type */}
                      {m.message_type === 'TEXT' && <p className="whitespace-pre-line">{m.body}</p>}
                      
                      {m.message_type === 'IMAGE' && m.file_url && (
                        <img src={getMediaUrl(m.file_url)} alt="attachment" className="rounded max-w-full h-auto cursor-pointer" onClick={() => window.open(getMediaUrl(m.file_url), '_blank')} />
                      )}

                      {m.message_type === 'AUDIO' && m.file_url && (
                        <audio controls src={getMediaUrl(m.file_url)} className="w-64 mt-1" />
                      )}

                      {m.message_type === 'FILE' && m.file_url && (
                        <a href={getMediaUrl(m.file_url)} target="_blank" rel="noreferrer" className={`flex items-center gap-2 p-2 rounded border ${isMine ? 'bg-emerald-700 border-emerald-500' : 'bg-gray-50 border-gray-200'}`}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
                          <span className="truncate underline">Download File</span>
                        </a>
                      )}

                      <div className={`flex items-center justify-end gap-1 mt-1 text-[10px] ${isMine ? 'text-emerald-100' : 'text-gray-400'}`}>
                        <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        {isMine && (
                          <span className="ml-1">{m.is_read ? <span className="text-blue-300 text-xs">✓✓</span> : <span className="text-emerald-200 text-xs">✓</span>}</span>
                        )}
                      </div>
                    </div>

                    {m.reactions.length > 0 && (
                      <div className={`flex gap-1 mt-1 z-10 ${isMine ? 'mr-2' : 'ml-2'}`}>
                        {m.reactions.map((r: any) => (
                          <span key={r.id} className="bg-white border rounded-full px-1.5 py-0.5 text-xs shadow-sm">{r.emoji}</span>
                        ))}
                      </div>
                    )}

                    <div className={`absolute top-0 -mt-3 opacity-0 group-hover:opacity-100 transition flex gap-1 ${isMine ? '-left-20' : '-right-20'}`}>
                      <button onClick={() => setReplyTo(m)} className="bg-white border p-1.5 rounded-full shadow hover:bg-gray-50 text-gray-500">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 17 4 12 9 7"></polyline><path d="M20 18v-2a4 4 0 0 0-4-4H4"></path></svg>
                      </button>
                      <button onClick={() => setShowEmojiFor(m.id)} className="bg-white border p-1.5 rounded-full shadow hover:bg-gray-50 text-gray-500">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>
                      </button>
                    </div>

                    {showEmojiFor === m.id && (
                      <div className={`absolute top-8 z-20 bg-white border shadow-lg rounded-full px-2 py-1 flex gap-2 ${isMine ? 'right-0' : 'left-0'}`}>
                        {['👍', '❤️', '😂', '😮', '😢', '🙏'].map(emoji => (
                          <button key={emoji} onClick={() => reactMutation.mutate({ msgId: m.id, emoji })} className="hover:scale-125 transition text-lg">{emoji}</button>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="border-t bg-white">
              {replyTo && (
                <div className="p-2 bg-gray-50 border-b flex justify-between items-center px-4">
                  <div className="border-l-4 border-emerald-500 pl-2 text-sm text-gray-600">
                    <span className="font-bold text-xs block">Replying to {replyTo.sender_email}</span>
                    <span className="truncate block max-w-lg">{replyTo.body || `[${replyTo.message_type}]`}</span>
                  </div>
                  <button onClick={() => setReplyTo(null)} className="text-gray-400 hover:text-red-500">✕</button>
                </div>
              )}
              <form onSubmit={(e) => { e.preventDefault(); if(text.trim()) sendMutation.mutate({ text, type: 'TEXT' }) }} className="p-4 flex gap-2 items-center">
                
                {/* Attachment Button */}
                <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
                <button type="button" onClick={() => fileInputRef.current?.click()} className="text-gray-500 hover:text-emerald-600 transition">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
                </button>

                {/* Input or Recording UI */}
                {isRecording ? (
                  <div className="flex-1 flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-full border border-red-200">
                    <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
                    <span className="text-sm font-medium">Recording voice note...</span>
                  </div>
                ) : (
                  <input 
                    type="text" value={text} onChange={e => setText(e.target.value)}
                    placeholder="Type a message..." 
                    className="flex-1 border rounded-full px-4 py-2 focus:outline-none focus:border-emerald-500 bg-gray-50"
                  />
                )}

                {/* Send or Mic Button */}
                {text.trim() ? (
                  <button type="submit" disabled={sendMutation.isPending} className="bg-emerald-600 text-white px-6 py-2 rounded-full font-medium hover:bg-emerald-700">Send</button>
                ) : (
                  <button 
                    type="button" 
                    onMouseDown={startRecording} 
                    onMouseUp={stopRecording}
                    onMouseLeave={stopRecording}
                    className={`p-2 rounded-full transition ${isRecording ? 'bg-red-600 text-white' : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'}`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
                  </button>
                )}
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
  
  sendMessage: (convId: string, body: string, replyToId?: string, file?: File, type: string = 'TEXT') => {
    const formData = new FormData()
    if (body) formData.append('body', body)
    formData.append('message_type', type)
    if (replyToId) formData.append('reply_to', replyToId)
    if (file) formData.append('file', file)
    
    return api(`/conversations/${convId}/messages/`, {
      method: 'POST', 
      body: formData
    })
  },
  
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
    print("Upgrading chat to support Voice Notes & Files...")
    
    # Update files
    (ROOT / "apps" / "messaging" / "models.py").write_text(MODELS.strip() + "\n", encoding="utf-8")
    (ROOT / "apps" / "messaging" / "serializers.py").write_text(SERIALIZERS.strip() + "\n", encoding="utf-8")
    (FRONTEND / "src" / "api" / "messaging.ts").write_text(API_FILE.strip() + "\n", encoding="utf-8")
    (FRONTEND / "src" / "pages" / "InboxPage.tsx").write_text(INBOX_PAGE.strip() + "\n", encoding="utf-8")

    print("Applying migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "messaging"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Done! Restart your backend and frontend.

Test it:
  1. Open two windows (seeker + landlord).
  2. In the chat input, click the Paperclip icon to upload an image or PDF.
  3. Click the Microphone icon to record a voice note. 
     (Hold it down, speak, release to send).
  4. You will see the media render directly in the chat bubbles.
""")

if __name__ == "__main__":
    run()