#!/usr/bin/env python3
"""NyumbaLink Phase 23: Maintenance & Work Orders."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend Files

MODELS = '''
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.properties.models import Property
from apps.management.models import Lease

class MaintenanceRequest(TimeStampedModel):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High / Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"

    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="maintenance_requests")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="maintenance_requests")
    lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True, blank=True, help_text="Optional: Link to specific tenant")
    
    title = models.CharField(max_length=128)
    description = models.TextField()
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = "maintenance request"
        verbose_name_plural = "maintenance requests"

    def __str__(self):
        return f"{self.title} - {self.property.neighbourhood.name} ({self.status})"
'''

SERIALIZERS = '''
from rest_framework import serializers
from .models import MaintenanceRequest

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.neighbourhood.name", read_only=True)
    tenant_name = serializers.CharField(source="lease.tenant_name", read_only=True, default="")
    
    class Meta:
        model = MaintenanceRequest
        fields = ("id", "property", "property_name", "lease", "tenant_name", "title", "description", "priority", "status", "resolved_at", "resolution_note", "created_at")
        read_only_fields = ("id", "landlord", "created_at", "resolved_at")
'''

VIEWS = '''
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import MaintenanceRequest
from .serializers import MaintenanceRequestSerializer

class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MaintenanceRequest.objects.filter(landlord=self.request.user).select_related("property", "lease")

    def perform_create(self, serializer):
        serializer.save(landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        req = self.get_object()
        new_status = request.data.get("status")
        note = request.data.get("resolution_note", "")
        
        if new_status not in ["OPEN", "IN_PROGRESS", "RESOLVED"]:
            return Response({"detail": "Invalid status"}, status=400)
            
        req.status = new_status
        req.resolution_note = note
        if new_status == "RESOLVED":
            req.resolved_at = timezone.now()
        req.save()
        return Response(MaintenanceRequestSerializer(req).data)
'''

URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaintenanceRequestViewSet

router = DefaultRouter()
router.register("maintenance", MaintenanceRequestViewSet, basename="maintenance")
urlpatterns = router.urls
'''

BACKEND_FILES = {
    "apps/maintenance/__init__.py": "",
    "apps/maintenance/apps.py": "from django.apps import AppConfig\n\nclass MaintenanceConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.maintenance'\n    label = 'maintenance'\n",
    "apps/maintenance/models.py": MODELS.strip() + "\n",
    "apps/maintenance/serializers.py": SERIALIZERS.strip() + "\n",
    "apps/maintenance/views.py": VIEWS.strip() + "\n",
    "apps/maintenance/urls.py": URLS.strip() + "\n",
    "apps/maintenance/admin.py": "from django.contrib import admin\nfrom .models import MaintenanceRequest\nadmin.site.register(MaintenanceRequest)\n",
    "apps/maintenance/migrations/__init__.py": "",
}

# ---------------------------------------------------------------- 2. Frontend API
FRONTEND_API = '''
import { api } from './client'

export const maintenanceApi = {
  list: () => api<{results: any[]}>('/maintenance/'),
  create: (data: any) => api('/maintenance/', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: string, note: string = '') => api(`/maintenance/${id}/update_status/`, {
    method: 'POST',
    body: JSON.stringify({ status, resolution_note: note })
  })
}
'''
(FRONTEND / "src" / "api" / "maintenance.ts").write_text(FRONTEND_API.strip() + "\n", encoding="utf-8")
print("Created src/api/maintenance.ts")

# ---------------------------------------------------------------- 3. Frontend Component
MAINTENANCE_PAGE = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { maintenanceApi } from '../api/maintenance'
import Loading from '../components/Loading'

export default function MaintenanceList() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ title: '', description: '', priority: 'MEDIUM', property: '', lease: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['maintenance'],
    queryFn: maintenanceApi.list,
  })

  // Assuming we have properties and leases for the dropdowns
  const { data: properties } = useQuery({ queryKey: ['properties-list'], queryFn: () => api('/properties/') })
  const { data: leases } = useQuery({ queryKey: ['leases-list'], queryFn: () => api('/leases/') })

  const createMutation = useMutation({
    mutationFn: () => maintenanceApi.create({ 
      ...formData, 
      lease: formData.lease || null 
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['maintenance'] }); setShowModal(false); setFormData({ title: '', description: '', priority: 'MEDIUM', property: '', lease: '' }) }
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => maintenanceApi.updateStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] })
  })

  if (isLoading) return <Loading />

  const columns = [
    { key: 'OPEN', label: 'Open Issues', color: 'border-red-500' },
    { key: 'IN_PROGRESS', label: 'In Progress', color: 'border-yellow-500' },
    { key: 'RESOLVED', label: 'Resolved', color: 'border-emerald-500' }
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Maintenance Board</h2>
        <button onClick={() => setShowModal(true)} className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium shadow-sm">
          + Log Issue
        </button>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {columns.map(col => (
          <div key={col.key} className={`bg-gray-50 rounded-lg p-4 border-t-4 ${col.color} shadow-inner`}>
            <h3 className="font-bold text-gray-700 mb-4">{col.label} ({data?.results.filter((r: any) => r.status === col.key).length})</h3>
            <div className="space-y-3">
              {data?.results.filter((r: any) => r.status === col.key).map((req: any) => (
                <div key={req.id} className="bg-white p-4 rounded shadow-sm border">
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      req.priority === 'HIGH' ? 'bg-red-100 text-red-800' : req.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                    }`}>{req.priority}</span>
                  </div>
                  <h4 className="font-bold text-gray-900">{req.title}</h4>
                  <p className="text-xs text-gray-500 mb-2">{req.property_name} {req.tenant_name ? `· ${req.tenant_name}` : ''}</p>
                  <p className="text-sm text-gray-700 line-clamp-3 mb-3">{req.description}</p>
                  
                  <div className="flex gap-2 border-t pt-3">
                    {req.status === 'OPEN' && (
                      <button onClick={() => updateMutation.mutate({ id: req.id, status: 'IN_PROGRESS' })} className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded hover:bg-yellow-200 w-full font-medium">Start Work</button>
                    )}
                    {req.status === 'IN_PROGRESS' && (
                      <button onClick={() => updateMutation.mutate({ id: req.id, status: 'RESOLVED' })} className="text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded hover:bg-emerald-200 w-full font-medium">Mark Resolved</button>
                    )}
                    {req.status === 'RESOLVED' && (
                      <p className="text-xs text-emerald-600 font-medium w-full text-center">✓ Completed {new Date(req.resolved_at).toLocaleDateString()}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Log Maintenance Issue</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }} className="p-6 space-y-3">
              <input required placeholder="Issue Title (e.g. Leaking Roof)" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <textarea required placeholder="Describe the problem..." rows={3} value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <select required value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="LOW">Low Priority</option>
                <option value="MEDIUM">Medium Priority</option>
                <option value="HIGH">High / Urgent</option>
              </select>
              <select required value={formData.property} onChange={e => setFormData({...formData, property: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">Select Property...</option>
                {properties?.results.map((p: any) => <option key={p.id} value={p.id}>{p.neighbourhood_name} ({p.property_type})</option>)}
              </select>
              <select value={formData.lease} onChange={e => setFormData({...formData, lease: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">No Specific Tenant</option>
                {leases?.results.map((l: any) => <option key={l.id} value={l.id}>{l.tenant_name}</option>)}
              </select>
              
              <button type="submit" disabled={createMutation.isPending} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 mt-2 font-medium">
                {createMutation.isPending ? 'Saving...' : 'Log Issue'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
'''
# Need to import api in the component for the query dropdowns
MAINTENANCE_PAGE = MAINTENANCE_PAGE.replace("import { maintenanceApi } from '../api/maintenance'", "import { maintenanceApi } from '../api/maintenance'\nimport { api } from '../api/client'")

(FRONTEND / "src" / "pages" / "MaintenanceList.tsx").write_text(MAINTENANCE_PAGE.strip() + "\n", encoding="utf-8")
print("Created src/pages/MaintenanceList.tsx")

# ---------------------------------------------------------------- 4. Patch Dashboard
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")
if "MaintenanceList" not in text:
    text = text.replace(
        "import TenantsList from './TenantsList'",
        "import TenantsList from './TenantsList'\nimport MaintenanceList from './MaintenanceList'"
    )
    
    # Add Tab Button
    old_tabs = '''        <button 
          onClick={() => setSearchParams({ tab: 'tenants' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'tenants' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Tenants
        </button>'''
    
    new_tabs = old_tabs + '''
        <button 
          onClick={() => setSearchParams({ tab: 'maintenance' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'maintenance' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Maintenance
        </button>'''
    
    text = text.replace(old_tabs, new_tabs)
    
    # Add Tab Content
    old_content = '''      ) : (
        <TenantsList />
      )}'''
    new_content = '''      ) : activeTab === 'tenants' ? (
        <TenantsList />
      ) : (
        <MaintenanceList />
      )}'''
    
    text = text.replace(old_content, new_content)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: added Maintenance tab")

# ---------------------------------------------------------------- 5. Execute
def run():
    print(f"NyumbaLink Phase 23 (Maintenance) -> {ROOT}\n")

    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.maintenance"' not in text:
        text = text.replace('    "apps.management",\n', '    "apps.management",\n    "apps.maintenance",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.maintenance.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.management.urls")),\n',
            'path("api/v1/", include("apps.management.urls")),\n    path("api/v1/", include("apps.maintenance.urls")),\n'
        )
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "maintenance"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 23 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as the Landlord (demo@nyumbalink.com).
  3. Go to Dashboard -> "Maintenance" tab.
  4. Click "+ Log Issue". Select a property, set priority to High, and describe the issue.
  5. You will see it appear in the "Open Issues" column.
  6. Click "Start Work" to move it to "In Progress".
  7. Click "Mark Resolved" to move it to the completed column.
""")

if __name__ == "__main__":
    run()