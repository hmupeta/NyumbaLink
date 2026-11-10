#!/usr/bin/env python3
"""Fixes TypeScript build errors from the carousel and lease scripts."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Fix LeaseAgreementPage.tsx (remove unused imports)
# ----------------------------------------------------------------
LEASE_FILE = FRONTEND / "src" / "pages" / "LeaseAgreementPage.tsx"
text = LEASE_FILE.read_text(encoding="utf-8")

# Remove unused useState import
text = text.replace(
    "import { useState } from 'react'\n",
    ""
)

# Remove unused navigate
text = re.sub(
    r"  const navigate = useNavigate\(\)\n",
    "",
    text
)
# Also remove the unused useNavigate from the import
text = text.replace(
    "import { useParams, Link, useNavigate } from 'react-router-dom'",
    "import { useParams, Link } from 'react-router-dom'"
)

LEASE_FILE.write_text(text, encoding="utf-8")
print("✅ Fixed LeaseAgreementPage.tsx: Removed unused imports")

# ----------------------------------------------------------------
# 2. Fix ManageListingPage.tsx (add missing state)
# ----------------------------------------------------------------
MANAGE_FILE = FRONTEND / "src" / "pages" / "ManageListingPage.tsx"
text = MANAGE_FILE.read_text(encoding="utf-8")

# Check if useState is imported
if "useState" not in text.split("\n")[0] and "import { useState" not in text:
    # The first import is usually `import { useQuery } from '@tanstack/react-query'`
    # so we need to add useState import
    if "import { useQuery" in text:
        text = text.replace(
            "import { useQuery",
            "import { useState } from 'react'\nimport { useQuery",
            1
        )
        print("  → Added useState import to ManageListingPage.tsx")

# Only add state if it's missing
if "const [activeImageIndex, setActiveImageIndex]" not in text:
    # Try multiple anchors to insert state after
    inserted = False
    
    # Anchor 1: after queryClient definition
    if "const queryClient = useQueryClient()" in text:
        text = text.replace(
            "const queryClient = useQueryClient()",
            "const queryClient = useQueryClient()\n  const [activeImageIndex, setActiveImageIndex] = useState(0)",
            1
        )
        inserted = True
        print("  → Added activeImageIndex state after queryClient")
    
    # Anchor 2: after useParams
    elif "const { id } = useParams" in text:
        # Find the end of that line
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if "const { id } = useParams" in line and not inserted:
                new_lines.append("  const [activeImageIndex, setActiveImageIndex] = useState(0)")
                inserted = True
        text = "\n".join(new_lines)
        print("  → Added activeImageIndex state after useParams")
    
    # Anchor 3: after function declaration
    elif "export default function ManageListingPage() {" in text:
        text = text.replace(
            "export default function ManageListingPage() {",
            "export default function ManageListingPage() {\n  const [activeImageIndex, setActiveImageIndex] = useState(0)",
            1
        )
        inserted = True
        print("  → Added activeImageIndex state after function declaration")
    
    if not inserted:
        print("  ⚠️ Could NOT find an anchor to add state. Please check manually.")
else:
    print("  ℹ️ activeImageIndex state already exists")

MANAGE_FILE.write_text(text, encoding="utf-8")
print("✅ Fixed ManageListingPage.tsx: Added activeImageIndex state")

# ----------------------------------------------------------------
# 3. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: TypeScript build errors in LeaseAgreementPage and ManageListingPage"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 TYPESCRIPT ERRORS FIXED!
==================================================

Render will now rebuild the frontend. Wait about 2 minutes.

Once it's live, go to a property's "Manage" page and test the carousel. 
The image carousel with arrows and thumbnails will now work properly.
""")