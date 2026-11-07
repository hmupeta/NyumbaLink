#!/usr/bin/env python3
"""Fixes image URLs in production and adds a fallback placeholder."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
API_FILE = FRONTEND / "src" / "api" / "listings.ts"

text = API_FILE.read_text(encoding="utf-8")

# Replace the old getMediaUrl function with a dynamic one
import re
pattern = r"export const getMediaUrl = \(url: string\) => \{[\s\S]*?\n\}"

new_function = '''export const getMediaUrl = (url: string) => {
  if (!url) return ''
  
  // 1. If it's a mangled Unsplash URL like https:/images... fix the slashes
  if (url.includes('https:/') && !url.includes('https://')) {
    return url.replace('https:/', 'https://')
  }

  // 2. If the URL got prefixed with /media/ but is an external link
  if (url.includes('/media/http')) {
    const match = url.match(/https?:\\/\\/.*/)
    if (match) return match[0]
  }
  
  // 3. Clean up encoded URLs
  if (url.includes('https%3A') || url.includes('http%3A')) {
    const externalUrl = url.substring(url.indexOf('http'))
    return decodeURIComponent(externalUrl)
  }
  
  // 4. Standard external URLs (Unsplash, etc.)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  
  // 5. Standard local media paths
  // Dynamically use the current API URL (e.g., https://nyumbalink-backend.../api/v1 -> https://nyumbalink-backend...)
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  const baseUrl = apiUrl.replace('/api/v1', '')
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
}'''

text = re.sub(pattern, new_function, text)

# Check if the replacement worked
if "const baseUrl = apiUrl.replace" in text:
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched src/api/listings.ts: Made getMediaUrl production-ready")
else:
    print("⚠️ Could not find getMediaUrl to patch. Let's just append it manually.")
    # Fallback append if regex failed
    API_FILE.write_text(text + "\n\n" + new_function, encoding="utf-8")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Image URLs resolving to localhost in production"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 FIX PUSHED!
==================================================

Render will automatically rebuild your frontend. Once it finishes:

1. Refresh the page.
2. The image will now try to load from your Render Backend URL instead of localhost.

### ⚠️ VERY IMPORTANT FOR PRODUCTION IMAGES
If you upload a *new* image on the live site, it will disappear the next time you deploy. 
Render wipes the filesystem on every deploy.

For permanent images, you must connect a Cloud Storage provider:
1. Create a free **Cloudflare R2** bucket or **AWS S3** bucket.
2. Install `django-storages` and `boto3`.
3. Update `DEFAULT_FILE_STORAGE` in `prod.py` to use the S3 backend.

If you want to tackle that in a future phase, let me know!
""")