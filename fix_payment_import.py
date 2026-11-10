#!/usr/bin/env python3
"""Fixes the PaymentTransaction import path."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
VIEWS_FILE = ROOT / "apps" / "payments" / "views.py"

text = VIEWS_FILE.read_text(encoding="utf-8")

# 1. Fix the import path
if "from .models import PaymentTransaction" in text:
    text = text.replace(
        "from .models import PaymentTransaction",
        "from apps.integrations.models import PaymentTransaction"
    )
    print("✅ Patched apps/payments/views.py: Fixed PaymentTransaction import")

# 2. Ensure Listing is imported
if "from apps.properties.models import Listing" not in text:
    text = "from apps.properties.models import Listing\n" + text
    print("✅ Patched apps/payments/views.py: Added Listing import")

VIEWS_FILE.write_text(text, encoding="utf-8")

# 3. Run Migrations to ensure everything is in sync
print("\n📦 Running makemigrations & migrate...")
subprocess.run([sys.executable, "manage.py", "makemigrations"], cwd=ROOT)
subprocess.run([sys.executable, "manage.py", "migrate"], cwd=ROOT)

# 4. Push to GitHub
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Import PaymentTransaction from integrations app"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 IMPORT FIXED AND PUSHED!
==================================================

Render will now build the backend successfully.
Wait ~2 minutes, then try initiating a payment on the mobile app!
""")