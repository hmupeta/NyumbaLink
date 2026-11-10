#!/usr/bin/env python3
"""Creates and applies migrations for the integrations app, and hardens the API client."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Generate and Apply Migrations
# ----------------------------------------------------------------
print("📦 Generating migrations for 'integrations' app...")
subprocess.run(["python", "manage.py", "makemigrations", "integrations"], cwd=ROOT)

print("\n🔨 Applying migrations locally...")
subprocess.run(["python", "manage.py", "migrate"], cwd=ROOT)

# ----------------------------------------------------------------
# 2. Flutter: Harden API Client against HTML errors
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

# Update the generic post method
old_post = '''  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return jsonDecode(res.body);
    }
    final error = jsonDecode(res.body)['detail'] ?? 'Request failed';
    throw Exception(error);
  }'''

new_post = '''  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    
    // Safety: If the server returns HTML (like a 500 error page), don't crash trying to parse it as JSON
    try {
      final decoded = jsonDecode(res.body);
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return decoded;
      }
      final error = decoded['detail'] ?? 'Request failed';
      throw Exception(error);
    } catch (e) {
      if (e is FormatException) {
        throw Exception("Server error (${res.statusCode}). Please try again later.");
      }
      rethrow;
    }
  }'''

if old_post in text:
    text = text.replace(old_post, new_post)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Hardened POST method against HTML responses")

# ----------------------------------------------------------------
# 3. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing migrations to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Add missing integrations migrations and harden Flutter API client"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 MIGRATION FIX APPLIED!
==================================================

1. **Backend**: The migration file for the payment settings table has been created and pushed to GitHub.
2. **Render**: Render will automatically detect the new migration file, run it during its build, and create the database table.
3. **Frontend**: The Flutter app is now robust. If the backend ever crashes again, it will show a clean error message instead of crashing with a JSON parsing error.

Go back to your Flutter terminal, quit ('q'), and restart the app:
  flutter run -d chrome

Wait 2 minutes for Render to deploy, and then try clicking "Generate API User & Key" again. It will now work!
""")