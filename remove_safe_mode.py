#!/usr/bin/env python3
"""Removes the Safe Mode screen and boots directly into the app."""
from pathlib import Path

ROOT = Path.cwd()
MAIN_FILE = ROOT / "mobile" / "lib" / "main.dart"

NEW_MAIN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';
import 'api_client.dart';
import 'login_screen.dart';

// Global keys for session timeout handling
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

void main() {
  // Set up the global 401 handler
  ApiClient.onUnauthorized = () {
    final context = navigatorKey.currentContext;
    if (context != null) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      
      // Only trigger the session expired redirect if the user was previously logged in.
      if (auth.user != null) {
        auth.logout();
        
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
      home: MainLayout(), // Direct boot into MainLayout
    );
  }
}
'''

MAIN_FILE.write_text(NEW_MAIN.strip() + "\n", encoding="utf-8")
print("✅ Removed Safe Mode. main.dart now boots directly to MainLayout.")

print("""
==================================================
🎉 SAFE MODE REMOVED!
==================================================

Go back to your Flutter terminal and press 'R' (capital R) for a full hot restart.

The app will now boot directly into your Home Screen with the bottom navigation bar!
""")