#!/usr/bin/env python3
"""Fixes the guest login loop and handles unauthenticated API calls gracefully."""
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Fix main.dart (Global 401 Handler)
# ----------------------------------------------------------------
MAIN_FILE = LIB / "main.dart"
text = MAIN_FILE.read_text(encoding="utf-8")

old_handler = '''  ApiClient.onUnauthorized = () {
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
  };'''

new_handler = '''  ApiClient.onUnauthorized = () {
    final context = navigatorKey.currentContext;
    if (context != null) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      
      // ONLY trigger the session expired redirect if the user was previously logged in.
      // If they are a guest, 401s are expected for protected endpoints.
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
  };'''

if old_handler in text:
    text = text.replace(old_handler, new_handler)
    MAIN_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched main.dart: Global 401 handler ignores guests")

# ----------------------------------------------------------------
# 2. Fix HomeScreen (Don't fetch notifications if guest)
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

old_init = '''  @override
  void initState() {
    super.initState();
    _fetchListings();
    _fetchNotifications();
  }'''

new_init = '''  @override
  void initState() {
    super.initState();
    _fetchListings();
    // Only fetch notifications if logged in
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user != null) {
        _fetchNotifications();
      }
    });
  }'''

if old_init in text:
    text = text.replace(old_init, new_init)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Only fetch notifications if authenticated")

# ----------------------------------------------------------------
# 3. Fix InboxScreen (Handle Guest gracefully)
# ----------------------------------------------------------------
INBOX_FILE = LIB / "inbox_screen.dart"
text = INBOX_FILE.read_text(encoding="utf-8")

if "Please log in to view your inbox." not in text:
    # We wrap the FutureBuilder logic to show a nice message instead of an error
    text = text.replace(
        'if (snapshot.hasError) return Center(child: Text("Error loading inbox. Please log in."));',
        'if (snapshot.hasError) return Center(child: Padding(padding: EdgeInsets.all(24), child: Text("Please log in to view your inbox.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey))));'
    )
    INBOX_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched inbox_screen.dart: Friendlier guest error")

# ----------------------------------------------------------------
# 4. Fix SavedScreen (Handle Guest gracefully)
# ----------------------------------------------------------------
SAVED_FILE = LIB / "saved_screen.dart"
text = SAVED_FILE.read_text(encoding="utf-8")

if "Please log in to view your saved properties." not in text:
    text = text.replace(
        'if (snapshot.hasError) return Center(child: Text("Error loading saved properties. Please log in."));',
        'if (snapshot.hasError) return Center(child: Padding(padding: EdgeInsets.all(24), child: Text("Please log in to view your saved properties.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey))));'
    )
    SAVED_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched saved_screen.dart: Friendlier guest error")

print("""
==================================================
🎉 GUEST LOOP FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.

1. Click "Continue Browsing as Guest" on the login screen.
2. It will take you to the Home feed to browse properties.
3. If you click the "Inbox" or "Saved" tabs, it will show a polite message asking you to log in, rather than crashing or kicking you out.
""")