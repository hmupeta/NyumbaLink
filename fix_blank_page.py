#!/usr/bin/env python3
"""Fixes the blank white page issue by cleaning up initState and Providers."""
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Rewrite main.dart to ensure it boots safely
# ----------------------------------------------------------------
MAIN_DART = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';
import 'api_client.dart';
import 'login_screen.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

void main() {
  // Catch any unhandled errors during app startup
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    print("FLUTTER ERROR: ${details.exception}");
  };

  ApiClient.onUnauthorized = () {
    final context = navigatorKey.currentContext;
    if (context != null) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user != null) {
        auth.logout();
        scaffoldMessengerKey.currentState?.showSnackBar(
          SnackBar(content: Text("Session expired. Please log in again."), backgroundColor: Colors.red)
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
      home: MainLayout(),
    );
  }
}
'''
(LIB / "main.dart").write_text(MAIN_DART.strip() + "\n", encoding="utf-8")
print("✅ Rewrote main.dart")

# ----------------------------------------------------------------
# 2. Fix home_screen.dart (Remove setState in initState, safe assets)
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

# Fix initState: remove setState wrapper around initial load
old_init = '''  void _fetchListings() {
    setState(() {
      _listings = ApiClient.getListings(
        query: _searchController.text,
        transactionType: _transactionType,
        propertyType: _propertyType,
        minBedrooms: _minBedrooms,
        maxPrice: _maxPrice,
      );
    });
  }'''
new_init = '''  void _fetchListings({bool fromInit = false}) {
    final future = ApiClient.getListings(
      query: _searchController.text,
      transactionType: _transactionType,
      propertyType: _propertyType,
      minBedrooms: _minBedrooms,
      maxPrice: _maxPrice,
    );

    if (fromInit) {
      _listings = future;
    } else {
      setState(() => _listings = future);
    }
  }'''
text = text.replace(old_init, new_init)

old_init_state = '''  @override
  void initState() {
    super.initState();
    _fetchListings();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user != null) {
        _fetchNotifications();
      }
    });
  }'''
new_init_state = '''  @override
  void initState() {
    super.initState();
    _fetchListings(fromInit: true);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user != null) {
        _fetchNotifications();
      }
    });
  }'''
text = text.replace(old_init_state, new_init_state)

# Fix the AppBar image (fallback if asset fails)
old_appbar = '''        title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 80),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),'''
new_appbar = '''        title: Row(
          children: [
            Image.asset(
              "assets/images/logo.png", 
              height: 50,
              errorBuilder: (context, error, stackTrace) => Icon(Icons.home, color: Colors.white, size: 30),
            ),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),'''
text = text.replace(old_appbar, new_appbar)

HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Patched home_screen.dart: Fixed initState and added asset fallback")

print("""
==================================================
🎉 BLANK PAGE FIX APPLIED!
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The blank page should now be resolved, and the app should boot directly to the Home screen with the intro card, login button, and map toggle.
""")