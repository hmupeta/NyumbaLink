#!/usr/bin/env python3
"""NyumbaLink Phase 22: Tenant & Lease Management."""
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

class Lease(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leases")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
    
    tenant_name = models.CharField(max_length=128)
    tenant_phone = models.CharField(max_length=20)
    tenant_email = models.EmailField(blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    def __str__(self):
        return f"{self.tenant_name} @ {self.property.neighbourhood.name}"

class RentRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="rent_records")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.lease.tenant_name} - {self.due_date.strftime('%b %Y')} ({self.status})"
'''

SERIALIZERS = '''
from rest_framework import serializers
from .models import Lease, RentRecord
from apps.properties.serializers import PropertySerializer

class RentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentRecord
        fields = ("id", "due_date", "amount", "paid_date", "status")
        read_only_fields = ("id",)

class LeaseSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.neighbourhood.name", read_only=True)
    rent_records = RentRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lease
        fields = ("id", "property", "property_name", "tenant_name", "tenant_phone", "tenant_email", "start_date", "end_date", "monthly_rent", "deposit_paid", "status", "rent_records", "created_at")
        read_only_fields = ("id", "landlord", "created_at")
'''

VIEWS = '''
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Lease, RentRecord
from .serializers import LeaseSerializer, RentRecordSerializer

class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lease.objects.filter(landlord=self.request.user).prefetch_related("rent_records")

    def perform_create(self, serializer):
        # When a lease is created, we automatically generate the first 12 rent records
        lease = serializer.save(landlord=self.request.user)
        
        # Simple logic to generate monthly rent records for the next 12 months
        import datetime
        current_date = lease.start_date
        for _ in range(12):
            RentRecord.objects.create(
                lease=lease,
                due_date=current_date,
                amount=lease.monthly_rent,
                status=RentRecord.Status.PENDING
            )
            # Add one month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

class RentRecordViewSet(viewsets.ModelViewSet):
    serializer_class = RentRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RentRecord.objects.filter(lease__landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        record = self.get_object()
        import datetime
        record.status = RentRecord.Status.PAID
        record.paid_date = datetime.date.today()
        record.save()
        return Response({"status": "paid"})
'''

URLS = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import LeaseViewSet, RentRecordViewSet

router = DefaultRouter()
router.register("leases", LeaseViewSet, basename="lease")

lease_router = routers.NestedDefaultRouter(router, "leases", lookup="lease")
lease_router.register("rent-records", RentRecordViewSet, basename="rent-record")

urlpatterns = router.urls + lease_router.urls
'''

BACKEND_FILES = {
    "apps/management/__init__.py": "",
    "apps/management/apps.py": "from django.apps import AppConfig\n\nclass ManagementConfig(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.management'\n    label = 'management'\n",
    "apps/management/models.py": MODELS.strip() + "\n",
    "apps/management/serializers.py": SERIALIZERS.strip() + "\n",
    "apps/management/views.py": VIEWS.strip() + "\n",
    "apps/management/urls.py": URLS.strip() + "\n",
    "apps/management/admin.py": "from django.contrib import admin\nfrom .models import Lease, RentRecord\nadmin.site.register([Lease, RentRecord])\n",
    "apps/management/migrations/__init__.py": "",
}

# ---------------------------------------------------------------- 2. Frontend API
FRONTEND_API = '''
import { api } from './client'

export const managementApi = {
  listLeases: () => api<{results: any[]}>('/leases/'),
  createLease: (data: any) => api('/leases/', { method: 'POST', body: JSON.stringify(data) }),
  markRentPaid: (leaseId: string, recordId: string) => api(`/leases/${leaseId}/rent-records/${recordId}/mark_paid/`, { method: 'POST' })
}
'''
(FRONTEND / "src" / "api" / "management.ts").write_text(FRONTEND_API.strip() + "\n", encoding="utf-8")
print("Created src/api/management.ts")

# ---------------------------------------------------------------- 3. Frontend Components
TENANTS_TAB = '''
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { managementApi } from '../api/management'
import Loading from '../components/Loading'

export default function TenantsList() {
  const queryClient = useQueryClient()
  const [expandedLease, setExpandedLease] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['leases'],
    queryFn: managementApi.listLeases,
  })

  const markPaidMutation = useMutation({
    mutationFn: ({ leaseId, recordId }: { leaseId: string, recordId: string }) => managementApi.markRentPaid(leaseId, recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['leases'] })
  })

  if (isLoading) return <Loading />

  return (
    <div className="space-y-4">
      {data?.results.length === 0 && (
        <div className="text-center py-12 bg-white rounded border">
          <p className="text-gray-500">You don't have any active tenants yet.</p>
        </div>
      )}
      
      {data?.results.map((lease: any) => {
        const pendingRent = lease.rent_records.filter((r: any) => r.status === 'PENDING')
        const isExpanded = expandedLease === lease.id

        return (
          <div key={lease.id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div 
              className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition"
              onClick={() => setExpandedLease(isExpanded ? null : lease.id)}
            >
              <div>
                <h3 className="font-bold text-lg text-gray-900">{lease.tenant_name}</h3>
                <p className="text-sm text-gray-600">{lease.property_name} · {lease.tenant_phone}</p>
                <p className="text-xs text-gray-500 mt-1">Lease ends: {new Date(lease.end_date).toLocaleDateString()}</p>
              </div>
              <div className="text-right">
                <p className="font-bold text-emerald-700">K {Number(lease.monthly_rent).toLocaleString()}/mo</p>
                <span className={`inline-block mt-1 px-2 py-1 rounded text-xs font-bold ${
                  pendingRent.length > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}>
                  {pendingRent.length > 0 ? `${pendingRent.length} Rent Unpaid` : 'Rent Up to Date'}
                </span>
              </div>
            </div>

            {/* Expanded Rent History */}
            {isExpanded && (
              <div className="border-t bg-gray-50 p-4">
                <h4 className="font-semibold text-sm text-gray-700 mb-3">Rent Schedule (Next 12 Months)</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {lease.rent_records.map((record: any) => (
                    <div key={record.id} className={`p-3 rounded border ${record.status === 'PAID' ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                      <p className="text-xs text-gray-500 font-medium">{new Date(record.due_date).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</p>
                      <p className="font-bold text-sm mt-1">K {Number(record.amount).toLocaleString()}</p>
                      
                      {record.status === 'PAID' ? (
                        <p className="text-xs text-green-700 font-medium mt-2 flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          Paid
                        </p>
                      ) : (
                        <button 
                          onClick={() => markPaidMutation.mutate({ leaseId: lease.id, recordId: record.id })}
                          className="mt-2 text-xs bg-gray-900 text-white px-2 py-1 rounded hover:bg-black w-full"
                        >
                          Mark Paid
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "TenantsList.tsx").write_text(TENANTS_TAB.strip() + "\n", encoding="utf-8")
print("Created src/pages/TenantsList.tsx")

# ---------------------------------------------------------------- 4. Add Tenant Modal (on Manage Listing Page)
MANAGE_FILE = FRONTEND / "src" / "pages" / "ManageListingPage.tsx"
text = MANAGE_FILE.read_text(encoding="utf-8")
if "Add Tenant" not in text:
    # Add state, mutation, and UI
    text = text.replace(
        "import { useQuery } from '@tanstack/react-query'",
        "import { useState } from 'react'\nimport { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'\nimport { managementApi } from '../api/management'"
    )
    text = text.replace(
        "export default function ManageListingPage() {",
        "export default function ManageListingPage() {\n  const queryClient = useQueryClient()\n  const [showTenantModal, setShowTenantModal] = useState(false)\n  const [tenantData, setTenantData] = useState({ tenant_name: '', tenant_phone: '', tenant_email: '', start_date: '', end_date: '', monthly_rent: '', deposit_paid: '' })"
    )
    
    # Add mutation
    text = text.replace(
        "  if (isLoading) return <Loading />",
        """  const addTenantMutation = useMutation({
    mutationFn: () => managementApi.createLease({ ...tenantData, property: listing?.property }),
    onSuccess: () => {
      setShowTenantModal(false)
      alert('Tenant added! Rent schedule generated.')
    },
    onError: () => alert('Failed to add tenant.')
  })

  if (isLoading) return <Loading />"""
    )
    
    # Add Button next to Edit
    text = text.replace(
        '<Link to={`/dashboard/listings/${listing.id}/edit`} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900 text-sm">\n          Edit Listing\n        </Link>',
        '''<div className="flex gap-2">
          <button onClick={() => setShowTenantModal(true)} className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 text-sm font-medium">
            + Add Tenant
          </button>
          <Link to={`/dashboard/listings/${listing.id}/edit`} className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-900 text-sm">
            Edit Listing
          </Link>
        </div>'''
    )

    # Add Modal at the bottom
    text = text.replace(
        "    </div>\n  )\n}",
        """      {showTenantModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-bold">Add New Tenant</h2>
              <button onClick={() => setShowTenantModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); addTenantMutation.mutate() }} className="p-6 space-y-3">
              <input required placeholder="Tenant Name" value={tenantData.tenant_name} onChange={e => setTenantData({...tenantData, tenant_name: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <input required placeholder="Phone Number (e.g. 0977123456)" value={tenantData.tenant_phone} onChange={e => setTenantData({...tenantData, tenant_phone: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <input type="email" placeholder="Email Address (optional)" value={tenantData.tenant_email} onChange={e => setTenantData({...tenantData, tenant_email: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                  <input type="date" required value={tenantData.start_date} onChange={e => setTenantData({...tenantData, start_date: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">End Date</label>
                  <input type="date" required value={tenantData.end_date} onChange={e => setTenantData({...tenantData, end_date: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
                </div>
              </div>
              <input type="number" required placeholder="Monthly Rent (ZMW)" value={tenantData.monthly_rent} onChange={e => setTenantData({...tenantData, monthly_rent: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <input type="number" placeholder="Deposit Paid (ZMW)" value={tenantData.deposit_paid} onChange={e => setTenantData({...tenantData, deposit_paid: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              
              <button type="submit" disabled={addTenantMutation.isPending} className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 mt-2 font-medium">
                {addTenantMutation.isPending ? 'Saving...' : 'Add Tenant & Generate Rent Schedule'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}"""
    )
    MANAGE_FILE.write_text(text, encoding="utf-8")
    print("Patched ManageListingPage.tsx: added Add Tenant modal")

# ---------------------------------------------------------------- 5. Patch Dashboard
DASHBOARD_FILE = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = DASHBOARD_FILE.read_text(encoding="utf-8")
if "TenantsList" not in text:
    text = text.replace(
        "import SavedSearchesList from './SavedSearchesList'",
        "import SavedSearchesList from './SavedSearchesList'\nimport TenantsList from './TenantsList'"
    )
    text = text.replace(
        "const activeTab = searchParams.get('tab') || 'listings'",
        "const activeTab = searchParams.get('tab') || 'listings'"
    )
    # Add Tab Button
    old_tabs = '''        <button 
          onClick={() => setSearchParams({ tab: 'searches' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'searches' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Saved Searches
        </button>'''
    
    new_tabs = old_tabs + '''
        <button 
          onClick={() => setSearchParams({ tab: 'tenants' })}
          className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'tenants' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500 hover:text-gray-800'}`}
        >
          Tenants
        </button>'''
    
    text = text.replace(old_tabs, new_tabs)
    
    # Add Tab Content
    old_content = '''      ) : (
        <SavedSearchesList />
      )}'''
    new_content = '''      ) : activeTab === 'searches' ? (
        <SavedSearchesList />
      ) : (
        <TenantsList />
      )}'''
    
    text = text.replace(old_content, new_content)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("Patched DashboardPage.tsx: added Tenants tab")

# ---------------------------------------------------------------- 6. Execute
def run():
    print(f"NyumbaLink Phase 22 (Tenant Management) -> {ROOT}\n")

    for rel, content in BACKEND_FILES.items():
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {rel}")

    settings_file = ROOT / "config" / "settings" / "base.py"
    text = settings_file.read_text(encoding="utf-8")
    if '"apps.management"' not in text:
        text = text.replace('    "apps.search",\n', '    "apps.search",\n    "apps.management",\n')
        settings_file.write_text(text, encoding="utf-8")
        print("  config/settings/base.py")

    urls_file = ROOT / "config" / "urls.py"
    text = urls_file.read_text(encoding="utf-8")
    if 'include("apps.management.urls")' not in text:
        text = text.replace(
            'path("api/v1/", include("apps.search.urls")),\n',
            'path("api/v1/", include("apps.search.urls")),\n    path("api/v1/", include("apps.management.urls")),\n'
        )
        urls_file.write_text(text, encoding="utf-8")
        print("  config/urls.py")

    print("\nApplying database migrations...")
    subprocess.run([sys.executable, "manage.py", "makemigrations", "management"])
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("""
Phase 22 Complete.

Test the flow:
  1. Restart backend and frontend.
  2. Log in as the Landlord (demo@nyumbalink.com).
  3. Go to Dashboard -> Manage a Listing.
  4. You will now see a green "+ Add Tenant" button next to Edit.
  5. Click it, fill in a tenant's name, rent, and dates. Submit.
  6. Go to the Dashboard -> "Tenants" tab.
  7. You will see the tenant, and a 12-month rent schedule automatically generated for you.
  8. You can click "Mark Paid" on the current month, and the UI will instantly update to show it's been collected!
""")

if __name__ == "__main__":
    run()