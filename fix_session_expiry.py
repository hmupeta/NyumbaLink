#!/usr/bin/env python3
"""Adds global session timeout handling and navigation to Flutter."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Flutter: Update main.dart for Global Navigation
# ----------------------------------------------------------------
MAIN_FILE = LIB / "main.dart"

NEW_MAIN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';
import 'api_client.dart';
import 'login_screen.dart';

// Global keys allow us to navigate or show SnackBars from anywhere in the app
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

void main() {
  // Set up the global 401 handler
  ApiClient.onUnauthorized = () {
    final context = navigatorKey.currentContext;
    if (context != null) {
      Provider.of<AuthProvider>(context, listen: false).logout();
      
      scaffoldMessengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Text("Session expired. Please log in again."),
          backgroundColor: Colors.red,
        )
      );
      
      navigatorKey.currentState?.pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => LoginScreen()),
        (Route<dynamic> route) => false,
      );
    }
  };

  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NyumbaLink',
      navigatorKey: navigatorKey,
      scaffoldMessengerKey: scaffoldMessengerKey,
      theme: ThemeData(primarySwatch: Colors.green),
      home: MainLayout(),
    );
  }
}
'''
MAIN_FILE.write_text(NEW_MAIN.strip() + "\n", encoding="utf-8")
print("✅ Patched main.dart: Added global navigator and 401 handler")

# ----------------------------------------------------------------
# 2. Flutter: Update ApiClient to intercept 401s
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

# Add the static callback at the top of the class
if "static VoidCallback? onUnauthorized;" not in text:
    text = text.replace(
        "class ApiClient {",
        "import 'package:flutter/material.dart';\n\nclass ApiClient {\n  static VoidCallback? onUnauthorized;"
    )

# Create a helper to check for 401s
if "static void _checkResponse(int statusCode)" not in text:
    text = text.replace(
        "  static Future<String?> getToken() async {",
        '''  static void _checkResponse(int statusCode) {
    if (statusCode == 401) {
      onUnauthorized?.call();
      throw Exception('Session expired');
    }
  }

  static Future<String?> getToken() async {'''
    )

# Inject the _checkResponse into all HTTP methods
# We use regex to find `if (res.statusCode ...` and add the check before it.
text = re.sub(
    r"(final res = await http\.(?:get|post|patch|delete)\([^;]+\);)\n\s*if \(res\.statusCode",
    r"\1\n    _checkResponse(res.statusCode);\n    if (res.statusCode",
    text
)

# Handle MultipartRequests (used for file uploads)
text = text.replace(
    "final response = await request.send();\n    if (response.statusCode != 201)",
    "final response = await request.send();\n    _checkResponse(response.statusCode);\n    if (response.statusCode != 201)"
)

API_FILE.write_text(text, encoding="utf-8")
print("✅ Patched api_client.dart: Injected global 401 interception")

print("""
==================================================
🎉 SESSION EXPIRY HANDLING COMPLETE!
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app.

### How it works now:
1. The app now has a global `navigatorKey`.
2. Every time an API call is made, `_checkResponse()` runs.
3. If the backend replies with a `401 Unauthorized` (expired token), the app instantly:
   - Clears the local token via `auth.logout()`.
   - Shows a red SnackBar: "Session expired. Please log in again."
   - Redirects the user to the `LoginScreen`.

This makes the app feel much more robust and user-friendly!
""")