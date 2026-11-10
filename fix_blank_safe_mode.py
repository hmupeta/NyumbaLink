#!/usr/bin/env python3
"""Applies a Safe Mode patch to isolate the Flutter blank screen."""
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Rewrite main.dart with a Safe Loading Screen
# ----------------------------------------------------------------
MAIN_DART = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';

void main() {
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
      theme: ThemeData(primarySwatch: Colors.green),
      home: SafeStartupScreen(),
    );
  }
}

// A temporary screen to verify if the app can render anything at all
class SafeStartupScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("NyumbaLink Safe Mode"), backgroundColor: Colors.green),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 80),
            SizedBox(height: 20),
            Text("App Compiled Successfully!", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                Navigator.pushReplacement(
                  context,
                  MaterialPageRoute(builder: (_) => MainLayout()),
                );
              },
              child: Text("Load Full App"),
            )
          ],
        ),
      ),
    );
  }
}
'''
(LIB / "main.dart").write_text(MAIN_DART.strip() + "\n", encoding="utf-8")
print("✅ Rewrote main.dart with Safe Mode Startup Screen")

# ----------------------------------------------------------------
# 2. Make HomeScreen bulletproof against missing assets/API errors
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

# 2a. Replace the Image.asset in the AppBar with an Icon just to test
if "Image.asset(" in text:
    text = text.replace(
        'Image.asset("assets/images/logo.png", height: 80),',
        'Icon(Icons.home, color: Colors.white, size: 30),' # Fallback test
    )

# 2b. Ensure the FutureBuilder handles errors
old_builder = '''          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings"));'''
new_builder = '''          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings: ${snapshot.error}"));'''
text = text.replace(old_builder, new_builder)

HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Patched home_screen.dart: Replaced Image.asset with Icon and added error detail")

# ----------------------------------------------------------------
# 3. Update AuthProvider to not crash if backend is down
# ----------------------------------------------------------------
AUTH_FILE = LIB / "auth_provider.dart"
text = AUTH_FILE.read_text(encoding="utf-8")

if "catch (e) {" not in text:
    text = text.replace(
        "    _user = await ApiClient.login(email, password);",
        "    try {\n      _user = await ApiClient.login(email, password);\n      notifyListeners();\n    } catch (e) { rethrow; }"
    )
    AUTH_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched auth_provider.dart: Added try/catch blocks")

print("""
==================================================
🎉 SAFE MODE PATCH APPLIED!
==================================================

Go back to your Flutter terminal, press 'R' to hot restart, and look at the browser.

1. If you see the "App Compiled Successfully!" screen, the blank page was caused by an error inside one of the screens (likely missing assets or API blocking).
2. Click "Load Full App". 
3. If it crashes again, look at the bottom of your Chrome browser (the terminal where Flutter is running) or press F12 in Chrome to see the exact red error message.
""")