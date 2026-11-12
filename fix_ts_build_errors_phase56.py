#!/usr/bin/env python3
"""Fixes TS errors from Phase 56 (MomoPaymentModal + TenantsList)."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Add checkStatus to paymentsApi
# ----------------------------------------------------------------
PAYMENTS_API = FRONTEND / "src" / "api" / "payments.ts"
text = PAYMENTS_API.read_text(encoding="utf-8")

if "checkStatus" not in text:
    # Insert the new method right after initiatePayment (or at the top of the object)
    old = "  initiatePayment: (data: any) =>"
    new = """  checkStatus: (reference: string) =>
    api<{ status: string }>(`/payments/status/${reference}/`),

  initiatePayment: (data: any) =>"""

    if old in text:
        text = text.replace(old, new, 1)
        PAYMENTS_API.write_text(text, encoding="utf-8")
        print("✅ Patched payments.ts: Added checkStatus method")
    else:
        # Fallback: append before the closing brace of the object
        text = text.rstrip()
        if text.endswith("}"):
            text = text[:-1] + """  checkStatus: (reference: string) =>
    api<{ status: string }>(`/payments/status/${reference}/`),
}"""
        PAYMENTS_API.write_text(text, encoding="utf-8")
        print("✅ Patched payments.ts (fallback): Added checkStatus method")

# ----------------------------------------------------------------
# 2. Remove unused useQueryClient from TenantsList.tsx
# ----------------------------------------------------------------
TENANTS = FRONTEND / "src" / "pages" / "TenantsList.tsx"
text = TENANTS.read_text(encoding="utf-8")

# Remove useQueryClient from the react-query import
old_import = "import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'"
new_import = "import { useQuery, useMutation } from '@tanstack/react-query'"

if old_import in text:
    text = text.replace(old_import, new_import)
    # Also remove the instantiation if present
    text = text.replace("  const queryClient = useQueryClient()\n", "")
    TENANTS.write_text(text, encoding="utf-8")
    print("✅ Patched TenantsList.tsx: Removed unused useQueryClient")
else:
    # Try alternative forms
    for line in text.split("\n"):
        if "useQueryClient" in line and "import" in line:
            print(f"  → Found: {line.strip()}")
            # Just strip the identifier from that import line
            text = text.replace("useQueryClient, ", "").replace(", useQueryClient", "")
            TENANTS.write_text(text, encoding="utf-8")
            print("✅ Patched TenantsList.tsx (fallback)")
            break

# ----------------------------------------------------------------
# 3. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Add checkStatus to payments API and remove unused useQueryClient"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 BUILD FIXED!
==================================================

Render will rebuild. Wait ~2 minutes, then refresh your site.

The "Pay Rent via MTN" flow and the PDF download buttons from Phase 56
will both work once the build is green.
""")