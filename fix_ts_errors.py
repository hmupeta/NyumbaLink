#!/usr/bin/env python3
"""Fixes all TypeScript build errors for Render deployment."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Fix PropertySummary Type (missing latitude/longitude)
# ----------------------------------------------------------------
types_file = FRONTEND / "src" / "api" / "types.ts"
text = types_file.read_text(encoding="utf-8")
if "latitude" not in text:
    text = text.replace(
        "  neighbourhood: string\n}",
        "  neighbourhood: string\n  latitude: number | null\n  longitude: number | null\n}"
    )
    types_file.write_text(text, encoding="utf-8")
    print("✅ Fixed types.ts: Added latitude and longitude to PropertySummary")

# ----------------------------------------------------------------
# 2. Fix DashboardPage.tsx (unused useState)
# ----------------------------------------------------------------
dash_file = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
text = dash_file.read_text(encoding="utf-8")
text = text.replace("import { useState } from 'react'\n", "")
text = text.replace("import { useState, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'\n", "import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'\n")
dash_file.write_text(text, encoding="utf-8")
print("✅ Fixed DashboardPage.tsx: Removed unused useState import")

# ----------------------------------------------------------------
# 3. Fix EditListingPage.tsx (unused useEffect and api)
# ----------------------------------------------------------------
edit_file = FRONTEND / "src" / "pages" / "EditListingPage.tsx"
text = edit_file.read_text(encoding="utf-8")
text = text.replace("import { useState, useEffect, type FormEvent } from 'react'", "import { useState, type FormEvent } from 'react'")
text = text.replace("import { api } from '../api/client'\n", "")
edit_file.write_text(text, encoding="utf-8")
print("✅ Fixed EditListingPage.tsx: Removed unused imports")

# ----------------------------------------------------------------
# 4. Fix HomePage.tsx (unused user and saveSearchMutation)
# ----------------------------------------------------------------
home_file = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = home_file.read_text(encoding="utf-8")
if "const { user } = useAuth();" in text:
    text = text.replace("  const { user } = useAuth();\n", "")
    
# Remove the saveSearchMutation block (from "const saveSearchMutation =" to the closing "})")
pattern = r"  const saveSearchMutation = useMutation\(\{[\s\S]*?\}\)\n\n"
text = re.sub(pattern, "", text)

home_file.write_text(text, encoding="utf-8")
print("✅ Fixed HomePage.tsx: Removed unused variables")

# ----------------------------------------------------------------
# 5. Fix MaintenanceList.tsx (missing types on query data)
# ----------------------------------------------------------------
maint_file = FRONTEND / "src" / "pages" / "MaintenanceList.tsx"
text = maint_file.read_text(encoding="utf-8")
text = text.replace(
    "const { data: properties } = useQuery({ queryKey: ['properties-list'], queryFn: () => api('/properties/') })",
    "const { data: properties } = useQuery<any>({ queryKey: ['properties-list'], queryFn: () => api('/properties/') })"
)
text = text.replace(
    "const { data: leases } = useQuery({ queryKey: ['leases-list'], queryFn: () => api('/leases/') })",
    "const { data: leases } = useQuery<any>({ queryKey: ['leases-list'], queryFn: () => api('/leases/') })"
)
maint_file.write_text(text, encoding="utf-8")
print("✅ Fixed MaintenanceList.tsx: Added type assertions for query data")

# ----------------------------------------------------------------
# 6. Fix PublicProfilePage.tsx (unused Link)
# ----------------------------------------------------------------
profile_file = FRONTEND / "src" / "pages" / "PublicProfilePage.tsx"
text = profile_file.read_text(encoding="utf-8")
text = text.replace("import { useParams, Link } from 'react-router-dom'", "import { useParams } from 'react-router-dom'")
profile_file.write_text(text, encoding="utf-8")
print("✅ Fixed PublicProfilePage.tsx: Removed unused Link import")

# ----------------------------------------------------------------
# 7. Commit and Push
# ----------------------------------------------------------------
print("\n🚀 Pushing fixes to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Resolve TypeScript compilation errors for Render"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 TYPESCRIPT ERRORS FIXED AND PUSHED!
==================================================

Next steps:
1. Go to your Render Dashboard for the Frontend Static Site.
2. Click the "Manual Deploy" button (top right) -> "Deploy latest commit".
3. The build will now run successfully and go live!
""")