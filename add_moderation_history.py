#!/usr/bin/env python3
"""Adds a History tab to the Moderation Console to track approvals."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Frontend API
MOD_API = FRONTEND / "src" / "api" / "moderation.ts"
text = MOD_API.read_text(encoding="utf-8")

if "getKycHistory" not in text:
    text = text.replace(
        "  rejectKYC: (id: string, reason: string) => api(`/verifications/${id}/reject/`, {\n    method: 'POST', body: JSON.stringify({ reason })\n  }),",
        "  rejectKYC: (id: string, reason: string) => api(`/verifications/${id}/reject/`, {\n    method: 'POST', body: JSON.stringify({ reason })\n  }),\n  getKycHistory: () => api<{results: any[]}>('/verifications/'),"
    )
    MOD_API.write_text(text, encoding="utf-8")
    print("Patched moderation.ts: added getKycHistory")

# ---------------------------------------------------------------- 2. Frontend Page
MOD_PAGE = FRONTEND / "src" / "pages" / "ModerationPage.tsx"
text = MOD_PAGE.read_text(encoding="utf-8")

# Update the tab state to include 'history'
text = text.replace(
    "const [activeTab, setActiveTab] = useState<'listings' | 'kyc' | 'reports'>('listings')",
    "const [activeTab, setActiveTab] = useState<'listings' | 'kyc' | 'reports' | 'history'>('listings')"
)

# Add the query
text = text.replace(
    "  const { data: reports, isLoading: loadingReports } = useQuery({",
    "  const { data: history, isLoading: loadingHistory } = useQuery({\n    queryKey: ['kyc-history'],\n    queryFn: moderationApi.getKycHistory,\n    enabled: activeTab === 'history',\n  })\n\n  const { data: reports, isLoading: loadingReports } = useQuery({"
)

# Add the Tab Button
text = text.replace(
    '''        <button onClick={() => setActiveTab('reports')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'reports' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Reports {reports?.results.length ? `(${reports.results.length})` : ''}
        </button>''',
    '''        <button onClick={() => setActiveTab('history')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'history' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          Approval History
        </button>
        <button onClick={() => setActiveTab('reports')} className={`pb-3 font-semibold text-sm transition border-b-2 ${activeTab === 'reports' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-gray-500'}`}>
          User Reports {reports?.results.length ? `(${reports.results.length})` : ''}
        </button>'''
)

# Add the History Tab Content (right before the REPORTS TAB comment)
old_reports_tab = "      {/* REPORTS TAB */}"
new_history_tab = '''      {/* HISTORY TAB */}
      {activeTab === 'history' && (
        <>
          {loadingHistory && <Loading />}
          {history?.results.length === 0 && <p className="text-gray-500 py-8">No KYC history found.</p>}
          <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-left">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 font-semibold text-sm">User</th>
                  <th className="px-4 py-3 font-semibold text-sm">Type</th>
                  <th className="px-4 py-3 font-semibold text-sm">Status</th>
                  <th className="px-4 py-3 font-semibold text-sm">Reviewed By</th>
                  <th className="px-4 py-3 font-semibold text-sm">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {history?.results.map((h: any) => (
                  <tr key={h.id}>
                    <td className="px-4 py-3 text-sm">{h.user_email}</td>
                    <td className="px-4 py-3 text-sm">{h.type_label}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        h.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                        h.status === 'REJECTED' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>{h.status}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">{h.reviewed_by_email || '-'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {h.reviewed_at ? new Date(h.reviewed_at).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* REPORTS TAB */}'''

text = text.replace(old_reports_tab, new_history_tab)
MOD_PAGE.write_text(text, encoding="utf-8")
print("Patched ModerationPage.tsx: added Approval History tab")

# ---------------------------------------------------------------- 3. Backend Serializer Fix
# We need to ensure the VerificationCaseSerializer returns the reviewed_by_email
SERIALIZER_FILE = ROOT / "apps" / "verification" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

if "reviewed_by_email" not in text:
    text = text.replace(
        '    status_label = serializers.CharField(source="get_status_display", read_only=True)',
        '    status_label = serializers.CharField(source="get_status_display", read_only=True)\n    user_email = serializers.CharField(source="user.email", read_only=True)\n    reviewed_by_email = serializers.CharField(source="reviewed_by.email", read_only=True)'
    )
    text = text.replace(
        '"rejection_reason", "documents", "created_at", "updated_at"',
        '"rejection_reason", "documents", "user_email", "reviewed_by_email", "reviewed_at", "created_at", "updated_at"'
    )
    SERIALIZER_FILE.write_text(text, encoding="utf-8")
    print("Patched verification/serializers.py: exposed user and reviewer emails")

print("""
Done! Restart your backend and frontend.

Now, if you click the "Approval History" tab, you will see every KYC request that has been approved or rejected, along with who did it.

To test the "Reports" tab:
  1. Log in as a Seeker.
  2. Go to a listing and click "Report this Listing" (at the bottom right).
  3. Fill out the form and submit.
  4. Log back in as the Superuser. The Reports tab will now show a (1)!
""")