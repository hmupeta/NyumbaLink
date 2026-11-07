#!/usr/bin/env python3
"""NyumbaLink Phase 25: Production Polish (Sentry & Resend Emails)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ---------------------------------------------------------------- 1. Backend: Requirements
REQ_FILE = ROOT / "requirements.txt"
text = REQ_FILE.read_text(encoding="utf-8")
if "django-anymail" not in text:
    text += "\ndjango-anymail[resend]>=10.0\nsentry-sdk[django]>=1.40\n"
    REQ_FILE.write_text(text, encoding="utf-8")
    print("✅ Updated requirements.txt")

# ---------------------------------------------------------------- 2. Backend: base.py (Add Anymail App)
BASE_FILE = ROOT / "config" / "settings" / "base.py"
text = BASE_FILE.read_text(encoding="utf-8")
if '"anymail"' not in text:
    text = text.replace(
        '    "rest_framework",\n',
        '    "rest_framework",\n    "anymail",\n'
    )
    BASE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched base.py: Added anymail to INSTALLED_APPS")

# ---------------------------------------------------------------- 3. Backend: prod.py (Sentry & Email config)
PROD_FILE = ROOT / "config" / "settings" / "prod.py"
text = PROD_FILE.read_text(encoding="utf-8")

if "sentry_sdk" not in text:
    sentry_config = '''
# ----------------------------------------------------------------
# ERROR TRACKING (Sentry)
# ----------------------------------------------------------------
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_dsn = os.environ.get("SENTRY_DSN", "")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1, # 10% of transactions for performance monitoring
        send_default_pii=True
    )

# ----------------------------------------------------------------
# EMAIL (Resend via Anymail)
# ----------------------------------------------------------------
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {
    "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
}
DEFAULT_FROM_EMAIL = "NyumbaLink <onboarding@resend.dev>" # Change to alerts@yourdomain.com later
'''
    text += sentry_config
    PROD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched prod.py: Added Sentry and Resend configurations")

# ---------------------------------------------------------------- 4. Frontend: Sentry
print("\n📦 Installing Sentry on Frontend...")
subprocess.run(["npm", "install", "@sentry/react"], cwd=FRONTEND, shell=True)

MAIN_TSX = FRONTEND / "src" / "main.tsx"
text = MAIN_TSX.read_text(encoding="utf-8")

if "Sentry.init" not in text:
    # We add Sentry initialization at the top of main.tsx
    sentry_import = '''
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || "",
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
'''
    text = sentry_import + text
    MAIN_TSX.write_text(text, encoding="utf-8")
    print("✅ Patched main.tsx: Initialized Sentry")

# ---------------------------------------------------------------- 5. Commit & Push
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Phase 25: Add Sentry error tracking and Resend emails"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 25 CODE PUSHED!
==================================================

Now you need to configure the API keys on Render.

### 1. Get your Sentry DSN (Error Tracking)
- Go to https://sentry.io and create a free account.
- Create two projects: one for "Django" and one for "React".
- Copy the DSN (Data Source Name) for both.

### 2. Get your Resend API Key (Emails)
- Go to https://resend.com and create a free account.
- Go to API Keys and generate a new key. Copy it.
- Note: The free tier lets you send to your own email for testing.
  To send to real users, you must verify a domain (e.g., nyumbalink.com).

### 3. Add Environment Variables on Render
- **Backend Service (nyumbalink-backend) -> Environment:**
  - Key: `SENTRY_DSN` | Value: (Your Django DSN)
  - Key: `RESEND_API_KEY` | Value: (Your Resend API Key)

- **Frontend Service (nyumbalink-frontend) -> Environment:**
  - Key: `VITE_SENTRY_DSN` | Value: (Your React DSN)

### 4. Trigger Deployments
Render should automatically pick up the latest GitHub push. Wait for both services to say "Live". Once they do, your app is now fully production-ready with error tracking and real emails!
""")