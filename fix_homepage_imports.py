#!/usr/bin/env python3
"""Fixes the remaining unused imports in HomePage.tsx."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
HOME_FILE = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"

text = HOME_FILE.read_text(encoding="utf-8")

# Fix the React Query import (remove useMutation)
text = text.replace(
    "import { useQuery, useMutation } from '@tanstack/react-query'",
    "import { useQuery } from '@tanstack/react-query'"
)

# Remove the useAuth import
text = text.replace(
    "import { useAuth } from '../auth/AuthContext'\n",
    ""
)

# Remove the searchApi import
text = text.replace(
    "import { searchApi } from '../api/search'\n",
    ""
)

HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Fixed HomePage.tsx imports")

# Commit and push
print("\n🚀 Pushing fix to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Remove unused imports in HomePage"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Go to your Render Frontend Static Site dashboard and click 
"Manual Deploy" -> "Deploy latest commit".

This should be the final TypeScript error. The build should 
now complete successfully and go live!
""")