#!/usr/bin/env python3
"""NyumbaLink Phase 26: SEO & Social Sharing."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Install Dependencies
print("📦 Installing react-helmet-async...")
subprocess.run(["npm", "install", "react-helmet-async"], cwd=FRONTEND, shell=True)

# ---------------------------------------------------------------- 2. Update main.tsx
MAIN_FILE = FRONTEND / "src" / "main.tsx"
text = MAIN_FILE.read_text(encoding="utf-8")

if "HelmetProvider" not in text:
    text = text.replace(
        "import { QueryClient, QueryClientProvider } from '@tanstack/react-query'",
        "import { QueryClient, QueryClientProvider } from '@tanstack/react-query'\nimport { HelmetProvider } from 'react-helmet-async'"
    )
    # Wrap the App in HelmetProvider
    text = text.replace(
        "    <QueryClientProvider client={queryClient}>",
        "    <HelmetProvider>\n    <QueryClientProvider client={queryClient}>"
    )
    text = text.replace(
        "    </QueryClientProvider>",
        "    </QueryClientProvider>\n    </HelmetProvider>"
    )
    MAIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched main.tsx: Added HelmetProvider")

# ---------------------------------------------------------------- 3. Update ListingDetailPage.tsx
DETAIL_FILE = FRONTEND / "src" / "pages" / "ListingDetailPage.tsx"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "Helmet" not in text:
    # Add imports
    text = text.replace(
        "import { useState, useEffect } from 'react'",
        "import { useState, useEffect } from 'react'\nimport { Helmet } from 'react-helmet-async'"
    )
    
    # Add Helmet tags right after the opening div of the return statement
    # We look for the `<div className="max-w-4xl mx-auto px-4 py-8">` or similar
    if '<div className="max-w-4xl mx-auto px-4 py-8">' in text:
        insert_point = '    <div className="max-w-4xl mx-auto px-4 py-8">\n'
        helmet_code = '''      <Helmet>
        <title>{listing.title} | NyumbaLink</title>
        <meta name="description" content={`${listing.property_summary.property_type} in ${listing.property_summary.neighbourhood}. ${listing.description?.slice(0, 150)}`} />
        
        {/* Open Graph tags for WhatsApp/Facebook */}
        <meta property="og:title" content={`${listing.title} | NyumbaLink`} />
        <meta property="og:description" content={`${listing.currency} ${Number(listing.price).toLocaleString()} · ${listing.property_summary.neighbourhood}`} />
        <meta property="og:type" content="website" />
        {images.length > 0 && <meta property="og:image" content={getMediaUrl(images[0].file)} />}
        <meta property="og:url" content={window.location.href} />
        
        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>
'''
        text = text.replace(insert_point, insert_point + helmet_code)
    
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched ListingDetailPage.tsx: Added Dynamic SEO Meta Tags")

# ---------------------------------------------------------------- 4. Add basic SEO to HomePage
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")
if "Helmet" not in text:
    text = text.replace(
        "import { useState, useEffect } from 'react'",
        "import { useState, useEffect } from 'react'\nimport { Helmet } from 'react-helmet-async'"
    )
    if '<div className="min-h-screen bg-gray-50 flex flex-col">' in text:
        insert_point = '    <div className="min-h-screen bg-gray-50 flex flex-col">\n'
        helmet_code = '''      <Helmet>
        <title>NyumbaLink | Find your place in Zambia</title>
        <meta name="description" content="The most trusted property marketplace in Zambia. Find houses, apartments, and land for rent or sale in Lusaka and beyond." />
        <meta name="keywords" content="Zambia property, houses for rent Lusaka, buy house Zambia, NyumbaLink" />
      </Helmet>
'''
        text = text.replace(insert_point, insert_point + helmet_code)
    
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched HomePage.tsx: Added Global SEO Meta Tags")

# ---------------------------------------------------------------- 5. Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Phase 26: Add SEO and Open Graph meta tags for social sharing"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 26 COMPLETE: SEO & SOCIAL SHARING!
==================================================

Once Render finishes building, try copying a property URL and pasting it 
into a WhatsApp chat. You will see a beautiful rich preview with the photo!

--------------------------------------------------
🌐 NEXT: CONNECTING A CUSTOM DOMAIN (Manual Step)
--------------------------------------------------
To look like a real business, you shouldn't use the `onrender.com` URL. 
If you buy a domain (e.g., from Namecheap or GoDaddy), here is how to connect it:

1. FRONTEND (nyumbalink.com):
   - Go to Render Frontend -> Settings -> Custom Domains.
   - Add 'nyumbalink.com' and 'www.nyumbalink.com'.
   - Render will give you CNAME/A records. Add these to your domain registrar's DNS settings.

2. BACKEND (api.nyumbalink.com):
   - Go to Render Backend -> Settings -> Custom Domains.
   - Add 'api.nyumbalink.com'.
   - Update your Frontend Environment Variable: 
     VITE_API_URL = https://api.nyumbalink.com/api/v1
   - Update your Backend ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS in prod.py to include the new domain.
""")