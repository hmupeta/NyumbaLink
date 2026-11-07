#!/usr/bin/env python3
"""Fixes the final media URL bugs for production."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
API_FILE = FRONTEND / "src" / "api" / "listings.ts"

text = API_FILE.read_text(encoding="utf-8")

# Replace the old getMediaUrl function entirely
pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"

new_function = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. Handle dummy seed data (e.g. https%3A/images.unsplash.com/... or /media/https%3A/...)
  if (url.includes('https%3A') || url.includes('http%3A') || url.includes('/media/http')) {
    const match = url.match(/https?(?:%3A|\:)/)
    if (match && match.index !== undefined) {
      const externalUrl = url.substring(match.index);
      return decodeURIComponent(externalUrl);
    }
  }
  
  // 2. Standard external URLs (like proper Unsplash links)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 3. Standard local media paths (Render backend)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''

text = re.sub(pattern, new_function, text)
API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched src/api/listings.ts: Upgraded getMediaUrl to handle all formats")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Final media URL resolution for production"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will rebuild the frontend.
Once it's live, the Unsplash dummy images will load correctly.

### ⚠️ HOW TO FIX UPLOADED IMAGES PERMANENTLY

Because Render wipes its hard drive on every deploy, you *must* use
cloud storage (like AWS S3 or Cloudinary) to store user-uploaded images.

The easiest and fastest way to fix this is using **Cloudinary** (it has a free tier).

1. Create a free account at https://cloudinary.com
2. Get your Cloud Name, API Key, and API Secret from the dashboard.
3. Run this command to install the required packages:
   pip install cloudinary django-cloudinary-storage
4. Add to requirements.txt:
   cloudinary>=1.36
   django-cloudinary-storage>=0.3.0
5. In config/settings/base.py, add 'cloudinary' and 'cloudinary_storage' to INSTALLED_APPS.
6. In config/settings/prod.py, add:
   import cloudinary
   cloudinary.config(
     cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
     api_key = os.environ.get('CLOUDINARY_API_KEY'),
     api_secret = os.environ.get('CLOUDINARY_API_SECRET')
   )
   DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

7. Add CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET
   to your Render Backend Environment Variables.

Once you do this, uploaded images will be stored in the cloud and will never
disappear when you redeploy!
""")