#!/usr/bin/env python3
"""Ensures PropertyAuthorityViewSet is defined, exported, and imported correctly."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()

VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
URLS_FILE  = ROOT / "apps" / "properties" / "urls.py"

# ----------------------------------------------------------------
# 1. Verify `PropertyAuthorityViewSet` exists in views.py
# ----------------------------------------------------------------
views_text = VIEWS_FILE.read_text(encoding="utf-8")

if "class PropertyAuthorityViewSet" not in views_text:
    print("⚠️ PropertyAuthorityViewSet is MISSING from views.py. Re-adding it now...")
    
    new_class = '''

class PropertyAuthorityViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyAuthoritySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        from django.db.models import Q
        from .models import PropertyAuthority
        return PropertyAuthority.objects.filter(
            Q(granted_by=self.request.user) | Q(granted_to=self.request.user)
        ).select_related("property", "granted_to")

    def perform_create(self, serializer):
        from django.contrib.auth import get_user_model
        from rest_framework import serializers as drf_serializers
        from .models import Property
        from apps.notifications.services import create_notification

        User = get_user_model()
        property_id = self.request.data.get("property")
        email = self.request.data.get("granted_to_email")

        prop = Property.objects.get(id=property_id)
        if prop.submitted_by != self.request.user:
            raise permissions.PermissionDenied("Only the property owner can grant authority.")

        agent = User.objects.filter(email__iexact=email).first()
        if not agent:
            raise drf_serializers.ValidationError("No user found with that email.")

        authority = serializer.save(
            property=prop,
            granted_to=agent,
            granted_by=self.request.user,
        )

        create_notification(
            user=agent,
            title="New Property Access",
            message=f"You have been granted access to manage {prop.neighbourhood.name}.",
            link="/dashboard",
        )
'''
    views_text = views_text.rstrip() + new_class
    VIEWS_FILE.write_text(views_text + "\n", encoding="utf-8")
    print("✅ Appended PropertyAuthorityViewSet to views.py")
else:
    print("ℹ️ PropertyAuthorityViewSet exists in views.py")

# ----------------------------------------------------------------
# 2. Ensure imports in views.py are correct
# ----------------------------------------------------------------
views_text = VIEWS_FILE.read_text(encoding="utf-8")

# Make sure PropertyAuthoritySerializer is imported
if "PropertyAuthoritySerializer" not in views_text.split("class ")[0]:
    if "from .serializers import (" in views_text:
        views_text = views_text.replace(
            "from .serializers import (",
            "from .serializers import (\n    PropertyAuthoritySerializer,"
        )
    else:
        views_text = "from .serializers import PropertyAuthoritySerializer\n" + views_text
    print("✅ Added PropertyAuthoritySerializer import to views.py")

VIEWS_FILE.write_text(views_text, encoding="utf-8")

# ----------------------------------------------------------------
# 3. Fix urls.py imports
# ----------------------------------------------------------------
urls_text = URLS_FILE.read_text(encoding="utf-8")

# Check whether PropertyAuthorityViewSet is in the import list from .views
import re
match = re.search(r"from \.views import ([^\n]+)", urls_text)

if match:
    imports = match.group(1)
    if "PropertyAuthorityViewSet" not in imports:
        new_imports = imports.rstrip() + ", PropertyAuthorityViewSet"
        urls_text = urls_text.replace(
            f"from .views import {imports}",
            f"from .views import {new_imports}"
        )
        print("✅ Added PropertyAuthorityViewSet to urls.py import list")
    else:
        print("ℹ️ PropertyAuthorityViewSet already imported in urls.py")
else:
    # If no import statement found, add one at the top
    urls_text = "from .views import PropertyAuthorityViewSet\n" + urls_text
    print("✅ Added new import line to urls.py")

URLS_FILE.write_text(urls_text, encoding="utf-8")

# ----------------------------------------------------------------
# 4. Final verification — make sure the file parses
# ----------------------------------------------------------------
try:
    compile(views_text, str(VIEWS_FILE), "exec")
    compile(urls_text, str(URLS_FILE), "exec")
    print("✅ Both files pass Python syntax check")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    raise SystemExit(1)

# ----------------------------------------------------------------
# 5. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Add missing PropertyAuthorityViewSet import in urls.py"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 IMPORT FIXED!
==================================================

Render will now build successfully.

Wait ~2 minutes, then test the Manage Agents panel on the Manage property page.
""")