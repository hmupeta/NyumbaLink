#!/usr/bin/env python3
"""NyumbaLink Phase 4: Trust & Verification Engine."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- Backend: Models
VERIFICATION_ENUMS = '''
from django.db import models

class VerificationType(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity Verification"
    OWNERSHIP_AUTHORITY = "OWNERSHIP_AUTHORITY", "Ownership / Authority"
    PROPERTY_PHYSICAL = "PROPERTY_PHYSICAL", "Physical Property Check"

class VerificationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
'''

VERIFICATION_MODELS = '''
import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from .enums import VerificationStatus, VerificationType

def verification_doc_path(instance, filename):
    return f"verifications/{instance.case.user_id}/{uuid.uuid4().hex}_{filename}"

class VerificationCase(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_cases")
    verification_type = models.CharField(max_length=32, choices=VerificationType.choices)
    status = models.CharField(max_length=16, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    
    # Admin fields
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verifications_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal admin notes")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "verification case"
        verbose_name_plural = "verification cases"
        constraints = [
            models.UniqueConstraint(fields=["user", "verification_type"], name="uniq_user_verification_type"),
        ]

    def __str__(self):
        return f"{self.get_verification_type_display()} - {self.user.email} ({self.status})"

class VerificationDocument(TimeStampedModel):
    case = models.ForeignKey(VerificationCase, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=verification_doc_path)
    document_type = models.CharField(max_length=64, help_text="e.g. NRC Front, Title Deed, Utility Bill")
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = "verification document"
        verbose_name_plural = "verification documents"
'''

VERIFICATION_ADMIN = '''
from django.contrib import admin
from django.utils import timezone
from .models import VerificationCase, VerificationDocument

class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    readonly_fields = ("file", "document_type")

@admin.register(VerificationCase)
class VerificationCaseAdmin(admin.ModelAdmin):
    list_display = ("user", "verification_type", "status", "created_at")
    list_filter = ("status", "verification_type")
    search_fields = ("user__email",)
    readonly_fields = ("user", "verification_type", "created_at", "updated_at")
    inlines = [VerificationDocumentInline]
    actions = ["approve_cases", "reject_cases"]

    @admin.action(description="Approve selected verifications")
    def approve_cases(self, request, queryset):
        queryset.update(status="APPROVED", reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} cases approved.")

    @admin.action(description="Reject selected verifications")
    def reject_cases(self, request, queryset):
        queryset.update(status="REJECTED", reviewed_by=request.user, reviewed_at=timezone.now(), rejection_reason="Rejected by admin.")
        self.message_user(request, f"{queryset.count()} cases rejected.")
'''

VERIFICATION_SERIALIZERS = '''
from rest_framework import serializers
from .models import VerificationCase, VerificationDocument

class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "file", "document_type", "created_at")

class VerificationCaseSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    type_label = serializers.CharField(source="get_verification_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = VerificationCase
        fields = ("id", "verification_type", "type_label", "status", "status_label", 
                  "rejection_reason", "documents", "created_at", "updated_at")
        read_only_fields = ("id", "status", "rejection_reason", "created_at", "updated_at")
'''

VERIFICATION_VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
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

class VerificationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post"]

    def perform_create(self, serializer):
        case_id = self.kwargs.get("case_pk")
        case = VerificationCase.objects.get(id=case_id, user=self.request.user)
        serializer.save(case=case)
'''

VERIFICATION_URLS = '''
from django.urls import path, include
from rest_framework_nested import routers
from .views import VerificationCaseViewSet, VerificationDocumentViewSet

router = routers.DefaultRouter()
router.register("verifications", VerificationCaseViewSet, basename="verification")

nested_router = routers.NestedDefaultRouter(router, "verifications", lookup="case")
nested_router.register("documents", VerificationDocumentViewSet, basename="verification-documents")

urlpatterns = router.urls + nested_router.urls
'''

# ---------------------------------------------------------------- Frontend: API & Page
FRONTEND_API = '''
import { api } from './client'

export interface VerificationDocument {
  id: string
  file: string
  document_type: string
  created_at: string
}

export interface VerificationCase {
  id: string
  verification_type: string
  type_label: string
  status: string
  status_label: string
  rejection_reason: string
  documents: VerificationDocument[]
  created_at: string
}

export const verificationApi = {
  list: () => api<{results: VerificationCase[]}>('/verifications/'),
  create: (verification_type: string) => api<VerificationCase>('/verifications/', {
    method: 'POST',
    body: JSON.stringify({ verification_type })
  }),
  uploadDocument: (caseId: string, file: File, document_type: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', document_type)
    return api(`/verifications/${caseId}/documents/`, { method: 'POST', body: formData })
  }
}
'''

VERIFICATION_PAGE = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { verificationApi, type VerificationCase } from '../api/verification'
import { getMediaUrl } from '../api/listings'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function VerificationPage() {
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  
  const { data, isLoading } = useQuery({
    queryKey: ['verifications'],
    queryFn: () => verificationApi.list(),
  })

  const cases = data?.results || []
  const identityCase = cases.find(c => c.verification_type === 'IDENTITY')
  const ownershipCase = cases.find(c => c.verification_type === 'OWNERSHIP_AUTHORITY')

  const createCase = useMutation({
    mutationFn: (type: string) => verificationApi.create(type),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['verifications'] }),
    onError: () => setError('Failed to start verification.')
  })

  const uploadDoc = useMutation({
    mutationFn: ({ caseId, file, type }: { caseId: string, file: File, type: string }) => 
      verificationApi.uploadDocument(caseId, file, type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['verifications'] })
      alert('Document uploaded successfully.')
    },
    onError: () => setError('Failed to upload document.')
  })

  const renderCase = (title: string, description: string, type: string, existingCase?: VerificationCase) => (
    <div className="bg-white border rounded-lg p-6 mb-6 shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-bold">{title}</h2>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        {existingCase && (
          <span className={`px-3 py-1 rounded text-xs font-bold ${
            existingCase.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
            existingCase.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
          }`}>
            {existingCase.status_label}
          </span>
        )}
      </div>

      {!existingCase ? (
        <button 
          onClick={() => createCase.mutate(type)}
          disabled={createCase.isPending}
          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 disabled:opacity-50 text-sm"
        >
          Start Verification
        </button>
      ) : (
        <div className="mt-4 border-t pt-4">
          {existingCase.status === 'REJECTED' && (
            <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">
              <strong>Rejected:</strong> {existingCase.rejection_reason}
            </div>
          )}
          
          <h3 className="text-sm font-semibold mb-2">Uploaded Documents</h3>
          <ul className="space-y-2 mb-4">
            {existingCase.documents.map(doc => (
              <li key={doc.id} className="text-sm flex items-center gap-2">
                <a href={getMediaUrl(doc.file)} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline">
                  {doc.document_type}
                </a>
                <span className="text-gray-400 text-xs">({new Date(doc.created_at).toLocaleDateString()})</span>
              </li>
            ))}
            {existingCase.documents.length === 0 && <li className="text-sm text-gray-500">No documents uploaded yet.</li>}
          </ul>

          {existingCase.status !== 'APPROVED' && (
            <div className="flex items-center gap-4">
              <input 
                type="file" 
                id={`file-${type}`}
                className="text-sm border rounded px-2 py-1"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    uploadDoc.mutate({ caseId: existingCase.id, file, type: 'Document' })
                    e.target.value = '' // reset
                  }
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Verification Center</h1>
        <p className="text-gray-600">Build trust by verifying your identity and property ownership.</p>
      </div>

      {error && <ErrorMessage message={error} />}
      {isLoading ? <Loading /> : (
        <div className="space-y-4">
          {renderCase(
            "Identity Verification",
            "Upload your NRC or Passport. This confirms who you are, but does not prove property ownership.",
            "IDENTITY",
            identityCase
          )}
          {renderCase(
            "Ownership / Authority",
            "Upload Title Deeds or a signed landlord authorization letter to prove you have the right to list this property.",
            "OWNERSHIP_AUTHORITY",
            ownershipCase
          )}
        </div>
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

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">
            NyumbaLink
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className="text-gray-700 hover:text-emerald-700 font-medium">
                  Dashboard
                </Link>
                <Link to="/verification" className="text-gray-700 hover:text-emerald-700 font-medium">
                  Verification
                </Link>
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                {user.is_staff && (
                  <a href="http://localhost:8000/admin/" className="text-emerald-700 hover:underline">
                    Admin
                  </a>
                )}
                <button onClick={handleLogout} className="text-gray-700 hover:text-red-600">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700">
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">
        NyumbaLink · Find your place. Connect your world.
      </footer>
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
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
'''

FRONTEND_FILES = {
    "src/api/verification.ts": FRONTEND_API,
    "src/pages/VerificationPage.tsx": VERIFICATION_PAGE,
    "src/components/Layout.tsx": LAYOUT,
    "src/App.tsx": APP_TSX,
}

BACKEND_FILES = {
    "apps/verification/__init__.py": "",
    "apps/verification/apps.py": "from django.apps import AppConfig\n\nclass VerificationConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.verification'\n    label = 'verification'\n",
    "apps/verification/enums.py": VERIFICATION_ENUMS.strip() + "\n",
    "apps/verification/models.py": VERIFICATION_MODELS.strip() + "\n",
    "apps/verification/admin.py": VERIFICATION_ADMIN.strip() + "\n",
    "apps/verification/serializers.py": VERIFICATION_SERIALIZERS.strip() + "\n",
    "apps/verification/views.py": VERIFICATION_VIEWS.strip() + "\n",
    "apps/verification/urls.py": VERIFICATION_URLS.strip() + "\n",
    "apps/verification/migrations/__init__.py": "",
}

def run():
    print(f"NyumbaLink Phase 4 (Verification) -> {ROOT}\n")
    
    print("Writing backend files:")
    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nPatching settings and urls:")
    # Patch settings
    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.verification"' not in text:
        text = text.replace('    "apps.properties",\n', '    "apps.properties",\n    "apps.verification",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")
    
    # Patch urls
    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.verification.urls")' not in text:
        text = text.replace('path("api/v1/", include("apps.properties.urls")),\n', 'path("api/v1/", include("apps.properties.urls")),\n    path("api/v1/", include("apps.verification.urls")),\n')
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nWriting frontend files:")
    for rel, content in FRONTEND_FILES.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "verification"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 4 Complete.

Next steps to test:

  1. Restart your frontend (npm run dev).

  2. In the browser, log in as demo@nyumbalink.com.
  3. Click "Verification" in the header.
  4. You will see two distinct cards: "Identity Verification" and "Ownership / Authority".
  5. Click "Start Verification" on Identity.
  6. Upload a dummy image file.
  7. The file will appear in the list.
  8. Log in to http://127.0.0.1:8000/admin/ as the superuser.
  9. Go to Verification -> Verification cases.
  10. Select the case, run the "Approve selected verifications" action.
  11. Go back to the frontend and refresh. The badge will now read "APPROVED".

This solidifies the trust foundation of NyumbaLink exactly as you specified: keeping identity separate from ownership authority.
""")

if __name__ == "__main__":
    run()