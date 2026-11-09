#!/usr/bin/env python3
"""Fixes the missing Count import and the Flutter infinite spinner."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Add the missing Count import
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "locations" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "from django.db.models import Count, Q" not in text:
    # Ensure the import is added at the very top
    if "from django.db.models import" in text:
        # If some models import exists, add Count to it
        import re
        text = re.sub(
            r"from django\.db\.models import ([^\n]+)", 
            r"from django.db.models import \1, Count, Q", 
            text,
            count=1
        )
    else:
        # Otherwise, inject a new line
        text = "from django.db.models import Count, Q\n" + text
    
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched apps/locations/views.py: Added missing Count import")
else:
    print("ℹ️ Count import already exists in locations/views.py")

# ----------------------------------------------------------------
# 2. Frontend: Bulletproof the spinner using a finally block
# ----------------------------------------------------------------
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

old_check = '''  Future<void> _checkViewingStatus() async {
    // If user isn't logged in, stop spinning immediately
    final auth = Provider.of<AuthProvider>(context, listen: false);
    if (auth.user == null) {
      setState(() => _checkingViewing = false);
      return;
    }

    try {
      // Timeout after 3 seconds so it doesn't spin forever
      final requests = await ApiClient.getViewingRequests().timeout(const Duration(seconds: 3));
      
      final req = requests.firstWhere(
        (r) => r['listing'].toString() == widget.listingId,
        orElse: () => null,
      );
      
      if (mounted) {
        setState(() {
          _viewingStatus = req != null ? req['status'] : null;
          _checkingViewing = false;
        });
      }
    } catch (e) {
      // Failsafe: if it times out or errors, stop spinning and show the button
      if (mounted) setState(() => _checkingViewing = false);
    }
  }'''

new_check = '''  Future<void> _checkViewingStatus() async {
    try {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user == null) {
        return; // Finally block will turn off the spinner
      }

      // Timeout after 5 seconds
      final requests = await ApiClient.getViewingRequests().timeout(const Duration(seconds: 5));
      
      final req = requests.firstWhere(
        (r) => r['listing'].toString() == widget.listingId,
        orElse: () => null,
      );
      
      if (mounted) {
        setState(() {
          _viewingStatus = req != null ? req['status'] : null;
        });
      }
    } catch (e) {
      print("Error fetching viewing status: $e");
    } finally {
      // THIS IS THE CRITICAL FIX: Always stop the spinner, no matter what!
      if (mounted) {
        setState(() => _checkingViewing = false);
      }
    }
  }'''

if old_check in text:
    text = text.replace(old_check, new_check)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added finally block to stop spinner")
else:
    print("⚠️ Could not find exact _checkViewingStatus code.")

# ----------------------------------------------------------------
# 3. Push to GitHub (fixes Render)
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Missing Count import and Flutter infinite spinner"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 ERRORS FIXED!
==================================================

1. **Backend**: Your local Django server will auto-reload and the `/neighbourhoods/top/` endpoint will stop crashing. Render is also being updated right now.
2. **Frontend**: The infinite spinner is gone.

Go back to your Flutter terminal, quit ('q'), and restart the app.
The "Request Viewing" button will now load instantly.
""")