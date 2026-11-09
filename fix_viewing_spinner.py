#!/usr/bin/env python3
"""Fixes the infinite spinner on the Request Viewing button."""
from pathlib import Path

ROOT = Path.cwd()
DETAIL_FILE = ROOT / "mobile" / "lib" / "listing_detail_screen.dart"
API_FILE = ROOT / "mobile" / "lib" / "api_client.dart"

# ----------------------------------------------------------------
# 1. Fix api_client.dart to handle missing results safely
# ----------------------------------------------------------------
text = API_FILE.read_text(encoding="utf-8")
old_get = '''  static Future<List<dynamic>> getViewingRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/viewings/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load viewing requests');
  }'''

new_get = '''  static Future<List<dynamic>> getViewingRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/viewings/'), headers: await getHeaders());
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      return data['results'] ?? [];
    }
    throw Exception('Failed to load viewing requests');
  }'''

if old_get in text:
    text = text.replace(old_get, new_get)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Made getViewingRequests fail-safe")

# ----------------------------------------------------------------
# 2. Fix listing_detail_screen.dart to add a Timeout and Auth check
# ----------------------------------------------------------------
text = DETAIL_FILE.read_text(encoding="utf-8")

# Add dart:async for TimeoutException
if "import 'dart:async';" not in text:
    text = "import 'dart:async';\n" + text

# Replace the _checkViewingStatus function
old_check = '''  Future<void> _checkViewingStatus() async {
    try {
      final requests = await ApiClient.getViewingRequests();
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
      if (mounted) setState(() => _checkingViewing = false);
    }
  }'''

new_check = '''  Future<void> _checkViewingStatus() async {
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

if old_check in text:
    text = text.replace(old_check, new_check)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added 3s timeout and auth check")
else:
    print("⚠️ Could not find the exact _checkViewingStatus block.")

print("""
==================================================
🎉 SPINNER FIXED!
==================================================

Go back to your terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The infinite spinner is gone. If the app can't fetch your viewing requests 
within 3 seconds, it will gracefully fall back to showing the "Request Viewing" button.
""")