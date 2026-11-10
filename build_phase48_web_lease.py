#!/usr/bin/env python3
"""NyumbaLink Phase 48b: Web Lease Agreement Signing Page."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. API Client Update
# ----------------------------------------------------------------
API_FILE = FRONTEND / "src" / "api" / "management.ts"
text = API_FILE.read_text(encoding="utf-8")

if "generateAgreement" not in text:
    text += '''
export const leaseApi = {
  get: (id: string) => api<any>(`/leases/${id}/`),
  generateAgreement: (id: string) => api<any>(`/leases/${id}/generate_agreement/`, { method: 'POST' }),
  sign: (id: string) => api<any>(`/leases/${id}/sign/`, { method: 'POST' }),
}
'''
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated management.ts API")

# ----------------------------------------------------------------
# 2. Create Lease Agreement Page
# ----------------------------------------------------------------
LEASE_PAGE = '''
import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leaseApi } from '../api/management'
import { useAuth } from '../auth/AuthContext'
import Loading from '../components/Loading'

export default function LeaseAgreementPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: lease, isLoading } = useQuery({
    queryKey: ['lease', id],
    queryFn: () => leaseApi.get(id!),
    enabled: !!id,
  })

  const generateMutation = useMutation({
    mutationFn: () => leaseApi.generateAgreement(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['lease', id] }),
  })

  const signMutation = useMutation({
    mutationFn: () => leaseApi.sign(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lease', id] })
      alert("Signature recorded!")
    },
  })

  if (isLoading || !lease) return <Loading />

  const isLandlord = user?.id === lease.landlord
  const isTenant = user?.email?.toLowerCase() === lease.tenant_email?.toLowerCase()
  const userSigned = isLandlord ? lease.landlord_signed : lease.tenant_signed
  const bothSigned = lease.landlord_signed && lease.tenant_signed

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/dashboard" className="text-sm text-emerald-700 hover:underline">← Back to Dashboard</Link>
      <h1 className="text-2xl font-bold mt-4 mb-2">Lease Agreement</h1>
      <p className="text-gray-600 mb-8">{lease.property_name} · {lease.tenant_name}</p>

      <div className="bg-white border rounded-lg shadow-sm p-8 mb-8">
        {!lease.agreement_text ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No agreement has been generated yet.</p>
            {isLandlord ? (
              <button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending} className="bg-emerald-600 text-white px-6 py-2 rounded hover:bg-emerald-700">
                {generateMutation.isPending ? 'Generating...' : 'Generate Lease Agreement'}
              </button>
            ) : (
              <p className="text-sm text-orange-600 font-medium">Waiting for Landlord to generate the document.</p>
            )}
          </div>
        ) : (
          <>
            <pre className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed mb-8">
              {lease.agreement_text}
            </pre>

            <div className="border-t pt-6 flex flex-col md:flex-row justify-between items-center gap-4">
              <div>
                <p className="text-sm text-gray-500">Landlord Signature:</p>
                <p className="font-bold text-lg">{lease.landlord_signed ? '✓ Signed' : 'Pending'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Tenant Signature:</p>
                <p className="font-bold text-lg">{lease.tenant_signed ? '✓ Signed' : 'Pending'}</p>
              </div>
            </div>

            {bothSigned ? (
              <div className="mt-6 bg-green-50 border border-green-200 text-green-800 p-4 rounded text-center font-bold">
                ✓ Contract Finalized. Property is now marked as OCCUPIED.
              </div>
            ) : (
              <div className="mt-6">
                {(isLandlord || isTenant) && !userSigned ? (
                  <button onClick={() => signMutation.mutate()} disabled={signMutation.isPending} className="w-full bg-blue-700 text-white py-3 rounded font-medium hover:bg-blue-800">
                    {signMutation.isPending ? 'Signing...' : 'Digitally Sign Agreement'}
                  </button>
                ) : (
                  <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 p-4 rounded text-center">
                    {userSigned ? "You have signed. Waiting for the other party." : "You are not a party to this lease."}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "LeaseAgreementPage.tsx").write_text(LEASE_PAGE.strip() + "\n", encoding="utf-8")
print("✅ Created LeaseAgreementPage.tsx")

# ----------------------------------------------------------------
# 3. Update App.tsx Routing
# ----------------------------------------------------------------
APP_FILE = FRONTEND / "src" / "App.tsx"
text = APP_FILE.read_text(encoding="utf-8")

if "LeaseAgreementPage" not in text:
    text = text.replace(
        "import PublicProfilePage from './pages/PublicProfilePage'",
        "import PublicProfilePage from './pages/PublicProfilePage'\nimport LeaseAgreementPage from './pages/LeaseAgreementPage'"
    )
    text = text.replace(
        '<Route path="/settings" element={<PaymentSettingsPage />} />',
        '<Route path="/settings" element={<PaymentSettingsPage />} />\n          <Route path="/leases/:id" element={<LeaseAgreementPage />} />'
    )
    APP_FILE.write_text(text, encoding="utf-8")
    print("✅ Added LeaseAgreementPage to App.tsx")

# ----------------------------------------------------------------
# 4. Add "Sign Lease" Button to Tenants Tab
# ----------------------------------------------------------------
TENANTS_FILE = FRONTEND / "src" / "pages" / "TenantsList.tsx"
text = TENANTS_FILE.read_text(encoding="utf-8")

if "Sign Lease" not in text:
    # Find the expanded view where the rent schedule is shown
    old_tile = '''                  <tr><td colSpan={5} className="p-8 text-center text-gray-500">No viewing requests yet.</td></tr>'''
    # Wait, TenantsList is a component, let's just add a button next to the tenant name.
    
    old_tenant_name = '''<h3 className="font-bold text-lg text-gray-900">{lease.tenant_name}</h3>'''
    new_tenant_name = '''<div className="flex items-center gap-4">
                        <h3 className="font-bold text-lg text-gray-900">{lease.tenant_name}</h3>
                        <a href={`/leases/${lease.id}`} className="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded hover:bg-emerald-200 transition">
                          Manage Lease / Sign
                        </a>
                      </div>'''
    
    text = text.replace(old_tenant_name, new_tenant_name)
    TENANTS_FILE.write_text(text, encoding="utf-8")
    print("✅ Added 'Manage Lease' button to TenantsList.tsx")

# ----------------------------------------------------------------
# 5. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Web UI for Lease Agreement and Signatures"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 48 COMPLETE!
==================================================

Render will now build the Web frontend. Wait about 2 minutes.

### How to test the full flow:
1. Log in as the Landlord (`landlord@nyumbalink.com`).
2. Go to **Dashboard -> Tenants**.
3. Click the new **"Manage Lease / Sign"** button next to the tenant.
4. Click **Generate Lease Agreement**. Read the legal document.
5. Click **Digitally Sign Agreement**. It will say "Waiting for the other party."
6. Log out, and log in as the Tenant (`seeker@nyumbalink.com`).
7. Go to `https://nyumbalink-frontend-pbkm.onrender.com/leases/<lease_id>` (or if you have a notification link, click it).
8. Click **Digitally Sign Agreement**.
9. The contract will finalize, the property disappears from the public listings, and it shows as `OCCUPIED`!
""")