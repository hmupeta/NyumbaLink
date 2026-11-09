#!/usr/bin/env python3
"""Fixes the missing action import in locations/views.py."""
from pathlib import Path

ROOT = Path.cwd()
VIEWS_FILE = ROOT / "apps" / "locations" / "views.py"

text = VIEWS_FILE.read_text(encoding="utf-8")

# 1. Ensure the 'action' import exists
if "from rest_framework.decorators import action" not in text:
    # Insert it right after the rest_framework imports
    if "from rest_framework import viewsets" in text:
        text = text.replace(
            "from rest_framework import viewsets, permissions, status",
            "from rest_framework import viewsets, permissions, status\nfrom rest_framework.decorators import action"
        )
        # Fallback if the exact string above isn't found
        if "from rest_framework.decorators import action" not in text:
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if "from rest_framework" in line:
                    lines.insert(i + 1, "from rest_framework.decorators import action")
                    break
            text = "\n".join(lines)
            
    print("✅ Added missing 'action' import")

# 2. Ensure the Count/Q imports exist
if "from django.db.models import Count, Q" not in text:
    if "from rest_framework import viewsets" in text:
         text = text.replace(
            "from rest_framework import viewsets, permissions, status",
            "from rest_framework import viewsets, permissions, status\nfrom django.db.models import Count, Q"
        )
    print("✅ Added missing Count/Q imports")

VIEWS_FILE.write_text(text, encoding="utf-8")
print("""
==================================================
🎉 IMPORTS FIXED!
==================================================

Your local Django server should automatically reload and start working.

If it doesn't, press Ctrl+C in your backend terminal and run:
  python manage.py runserver
""")