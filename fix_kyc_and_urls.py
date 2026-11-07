#!/usr/bin/env python3
"""Fixes KYC routing, improves document viewing UX, and fixes media URLs."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Fix Backend Views
VIEWS_FILE = ROOT / "apps" / "verification" / "views.py"

# We completely rewrite the file to ensure methods are inside the class
VIEWS_CODE = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.notifications.services import create_notification
from .models import VerificationCase, VerificationDocument
from .serializers import VerificationCaseSerializer, VerificationDocumentSerializer

class VerificationCaseViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return VerificationCase.objects.all().prefetch_related("documents")
        return VerificationCase.objects.filter(user=self.request.user).prefetch_related("documents")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can approve."}, status=status.HTTP_403_FORBIDDEN)
        
        case = self.get_object()
        case.status = "APPROVED"
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Approved",
            message=f"Your {case.get_verification_type_display()} has been approved!",
            link=f"/profiles/{case.user.id}"
        )
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only staff can reject."}, status=status.HTTP_403_FORBIDDEN)
        
        case = self.get_object()
        reason = request.data.get("reason", "Documents unclear or invalid.")
        case.status = "REJECTED"
        case.rejection_reason = reason
        case.reviewed_by = request.user
        case.reviewed_at = timezone.now()
        case.save()

        create_notification(
            user=case.user,
            title="Verification Rejected",
            message=f"Your {case.get_verification_type_display()} was rejected: {reason}",
            link=f"/verification"
        )
        return Response({"status": "rejected"})

class VerificationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post"]

    def perform_create(self, serializer):
        case_id = self.kwargs.get("case_pk")
        case = VerificationCase.objects.get(id=case_id, user=self.request.user)
        serializer.save(case=case)
'''
VIEWS_FILE.write_text(VIEWS_CODE.strip() + "\n", encoding="utf-8")
print("Patched apps/verification/views.py: fixed routing and actions")

# ---------------------------------------------------------------- 2. Fix Frontend getMediaUrl
LISTINGS_API = FRONTEND / "src" / "api" / "listings.ts"
text = LISTINGS_API.read_text(encoding="utf-8")

old_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  if (url.startsWith('http')) return url
  return `http://localhost:8000${url}`
}'''

new_url_logic = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // Clean up encoded URLs (from dummy seed data)
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // If it's already an external URL (like Unsplash), return it directly
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // Sometimes Django pre-formats the URL incorrectly with a single slash
  if (url.startsWith('/media/https:/')) {
     return 'https://' + url.replace('/media/https:/', '')
  }

  // Otherwise, it's a local media file
  return `http://localhost:8000${url.startsWith('/') ? '' : '/'}${url}`
}'''

text = text.replace(old_url_logic, new_url_logic)
LISTINGS_API.write_text(text, encoding="utf-8")
print("Patched src/api/listings.ts: bulletproofed getMediaUrl")

# ---------------------------------------------------------------- 3. Improve Moderation UI
MODERATION_FILE = FRONTEND / "src" / "pages" / "ModerationPage.tsx"
text = MODERATION_FILE.read_text(encoding="utf-8")

# Replace the document mapping block
old_docs = '''                  <div className="flex gap-4">
                    {kyc.documents.map((doc: any) => (
                      <a key={doc.id} href={getMediaUrl(doc.file)} target="_blank" rel="noreferrer" className="flex items-center gap-2 bg-white border px-3 py-2 rounded shadow-sm hover:shadow-md transition">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                        <span className="text-sm font-medium text-gray-700">{doc.document_type}</span>
                      </a>
                    ))}
                    {kyc.documents.length === 0 && <span className="text-sm text-gray-400">No documents uploaded.</span>}
                  </div>'''

new_docs = '''                  <div className="flex flex-wrap gap-4">
                    {kyc.documents.map((doc: any) => (
                      <a 
                        key={doc.id} 
                        href={getMediaUrl(doc.file)} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 px-4 py-2 rounded-lg shadow-sm hover:shadow hover:bg-emerald-100 transition group"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#047857" strokeWidth="2" className="group-hover:scale-110 transition-transform"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        <span className="text-sm font-bold text-emerald-800">View {doc.document_type}</span>
                      </a>
                    ))}
                    {kyc.documents.length === 0 && <span className="text-sm text-gray-400">No documents uploaded.</span>}
                  </div>'''

text = text.replace(old_docs, new_docs)
MODERATION_FILE.write_text(text, encoding="utf-8")
print("Patched src/pages/ModerationPage.tsx: improved document viewing UX")

print("""
Done! Next steps:
  1. Restart your backend server (Ctrl+C, then runserver).
  2. Restart your frontend (npm run dev).
  3. Go to Moderation -> KYC Requests.
  4. You will now see a distinct green button labeled "View [Document Type]" for every uploaded file.
  5. Click it to view the document in a new tab.
  6. Click Reject or Approve. It will now successfully update the database (no more 404 error!).
""")