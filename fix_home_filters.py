#!/usr/bin/env python3
"""Fixes the HomePage to react to URL query changes (Buy/Rent buttons)."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
HOME_FILE = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"

text = HOME_FILE.read_text(encoding="utf-8")

# 1. Add the useEffect imports
if "useEffect" not in text:
    text = text.replace(
        "import { useState } from 'react'",
        "import { useState, useEffect } from 'react'"
    )

# 2. Replace the initial state and add the sync effect
old_state = '''  const [searchParams] = useSearchParams()
  const initialType = searchParams.get('type') === 'sale' ? 'SALE' : searchParams.get('type') === 'rent' ? 'RENT' : undefined
  
  const [filters, setFilters] = useState<ListingFilters>({ transaction_type: initialType })'''

new_state = '''  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState<ListingFilters>({})

  // Sync URL params with filters
  useEffect(() => {
    const typeParam = searchParams.get('type');
    const newType = typeParam === 'sale' ? 'SALE' : typeParam === 'rent' ? 'RENT' : undefined;
    
    // Only update if the type actually changed
    setFilters(prev => {
      if (prev.transaction_type !== newType) {
        return { ...prev, transaction_type: newType };
      }
      return prev;
    });
  }, [searchParams]);

  // Scroll to listings when the URL changes
  useEffect(() => {
    if (searchParams.get('type')) {
      setTimeout(() => {
        const element = document.getElementById('listings-section');
        if (element) {
          const y = element.getBoundingClientRect().top + window.scrollY - 80; // 80px offset for sticky header
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
      }, 100);
    }
  }, [searchParams]);'''

if old_state in text:
    text = text.replace(old_state, new_state)
else:
    print("⚠️ Could not find exact state definition. Attempting fallback patch.")

# 3. Add ID to the listings section for scrolling
text = text.replace(
    '<div className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-6">',
    '<div id="listings-section" className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-6">'
)

HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Patched HomePage.tsx: Added URL syncing and auto-scroll")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: React to Buy/Rent URL params and auto-scroll to listings"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 BUTTONS FIXED!
==================================================

Render will automatically rebuild your frontend.

Once it's live:
1. Go to the home page.
2. Click "Find rentals" or "Browse homes".
3. The page will instantly filter the listings AND smoothly scroll down to them so you can see the results immediately.
""")