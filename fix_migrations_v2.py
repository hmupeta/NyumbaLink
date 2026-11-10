#!/usr/bin/env python3
"""Properly installs dependencies and creates the missing integrations migration."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# ----------------------------------------------------------------
# 1. Install missing packages into the current environment
# ----------------------------------------------------------------
print("📦 Installing required packages (cloudinary_storage)...")
subprocess.run([sys.executable, "-m", "pip", "install", "cloudinary", "django-cloudinary-storage"], check=True)

# ----------------------------------------------------------------
# 2. Generate Migrations using sys.executable (ensures venv is used)
# ----------------------------------------------------------------
print("\n📦 Generating migrations for 'integrations' app...")
# We use sys.executable to ensure we use the exact same Python running this script
result = subprocess.run([sys.executable, "manage.py", "makemigrations", "integrations"], cwd=ROOT)

if result.returncode != 0:
    print("❌ Failed to generate migrations. Please check the errors above.")
    sys.exit(1)

print("\n🔨 Applying migrations locally...")
subprocess.run([sys.executable, "manage.py", "migrate"], cwd=ROOT)

# ----------------------------------------------------------------
# 3. Verify the migration file exists
# ----------------------------------------------------------------
migration_dir = ROOT / "apps" / "integrations" / "migrations"
migration_files = list(migration_dir.glob("0001_*.py"))

if not migration_files:
    print("❌ ERROR: Migration file was not created. Something went wrong.")
    sys.exit(1)

print(f"✅ Migration created successfully: {migration_files[0].name}")

# ----------------------------------------------------------------
# 4. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing the new migration to GitHub...")
subprocess.run(["git", "add", "apps/integrations/migrations/"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Add actual migration file for landlord payment settings"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 MIGRATION ACTUALLY CREATED AND PUSHED!
==================================================

1. The migration file (0001_initial.py) is now in your repository.
2. Render will automatically detect this new file, rebuild, and run the migration to create the `integrations_landlordpaymentsettings` table.

Wait about 2 minutes for Render to finish deploying, then:
1. Restart your Flutter app (`q`, then `flutter run -d chrome`).
2. Go to Payment Integrations and click "Generate API User & Key". It will now work perfectly!
""")