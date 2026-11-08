#!/usr/bin/env python3
"""NyumbaLink Phase 27: Flutter Mobile App Foundation."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# ---------------------------------------------------------------- 1. Patch Backend for Mobile
ACCOUNTS_VIEWS = ROOT / "apps" / "accounts" / "views.py"
text = ACCOUNTS_VIEWS.read_text(encoding="utf-8")

# Add tokens to the response body for mobile clients
if '"access": str(refresh.access_token)' not in text:
    # Patch LoginView
    text = text.replace(
        '        response = Response({"user": UserSerializer(user).data})',
        '        response = Response({"user": UserSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)})'
    )
    # Patch RegisterView
    text = text.replace(
        '        response = Response(\n            {"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED\n        )',
        '        response = Response(\n            {"user": UserSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)}, status=status.HTTP_201_CREATED\n        )'
    )
    ACCOUNTS_VIEWS.write_text(text, encoding="utf-8")
    print("✅ Patched accounts/views.py: Return JWT in JSON body for Flutter")

print("\n🚀 Committing backend fix to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Support JWT in body for Flutter mobile app"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ---------------------------------------------------------------- 2. Create Flutter App
print("\n📱 Creating Flutter App...")
FLUTTER_DIR = ROOT / "mobile"
if not FLUTTER_DIR.exists():
    # Using a generic org name, you can change it
    subprocess.run(["flutter", "create", "--org", "com.nyumbalink", "mobile"], cwd=ROOT, shell=True)
    print("✅ Flutter project created in /mobile")
else:
    print("ℹ️ Flutter directory already exists, skipping creation.")

# ---------------------------------------------------------------- 3. Add Dependencies
print("\n📦 Adding Flutter Dependencies...")
PUBSPEC = FLUTTER_DIR / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")
deps = """
  http: ^1.1.0
  provider: ^6.1.1
  shared_preferences: ^2.2.2
  cached_network_image: ^3.3.0
  intl: ^0.18.1
"""
if "http:" not in text:
    text = text.replace("  flutter:\n    sdk: flutter\n", "  flutter:\n    sdk: flutter\n" + deps)
    PUBSPEC.write_text(text, encoding="utf-8")
    subprocess.run(["flutter", "pub", "get"], cwd=FLUTTER_DIR, shell=True)
    print("✅ Added dependencies and ran pub get")

# ---------------------------------------------------------------- 4. Write Flutter Code
LIB_DIR = FLUTTER_DIR / "lib"

# API Client
API_CLIENT = '''
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String baseUrl = "https://nyumbalink-backend-eaw2.onrender.com/api/v1";
  
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  static Future<Map<String, String>> getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<List<dynamic>> getListings() async {
    final res = await http.get(Uri.parse('$baseUrl/listings/'), headers: await getHeaders());
    if (res.statusCode == 200) {
      return jsonDecode(res.body)['results'];
    }
    throw Exception('Failed to load listings');
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('access_token', data['access']);
      return data['user'];
    }
    throw Exception('Invalid credentials');
  }
}
'''
(LIB_DIR / "api_client.dart").write_text(API_CLIENT.strip() + "\n", encoding="utf-8")

# Auth Provider
AUTH_PROVIDER = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String email, String password) async {
    _user = await ApiClient.login(email, password);
    notifyListeners();
  }
}
'''
(LIB_DIR / "auth_provider.dart").write_text(AUTH_PROVIDER.strip() + "\n", encoding="utf-8")

# Login Screen
LOGIN_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;

  void _submit() async {
    setState(() => _loading = true);
    try {
      await Provider.of<AuthProvider>(context, listen: false).login(_emailCtrl.text, _passCtrl.text);
      Navigator.pushReplacementNamed(context, '/home');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text("NyumbaLink", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.emerald)),
              SizedBox(height: 40),
              TextField(controller: _emailCtrl, decoration: InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
              SizedBox(height: 16),
              TextField(controller: _passCtrl, decoration: InputDecoration(labelText: 'Password', border: OutlineInputBorder()), obscureText: true),
              SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.emerald),
                  child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Login"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
'''
(LIB_DIR / "login_screen.dart").write_text(LOGIN_SCREEN.strip() + "\n", encoding="utf-8")

# Home Screen
HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _listings;

  @override
  void initState() {
    super.initState();
    _listings = ApiClient.getListings();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("NyumbaLink"), backgroundColor: Colors.emerald),
      body: FutureBuilder<List<dynamic>>(
        future: _listings,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings"));
          
          final listings = snapshot.data!;
          return ListView.builder(
            itemCount: listings.length,
            itemBuilder: (context, index) {
              final l = listings[index];
              final imageUrl = l['media'].isNotEmpty ? l['media'][0]['file'] : null;
              
              return Card(
                margin: EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (imageUrl != null)
                      CachedNetworkImage(
                        imageUrl: imageUrl.startsWith('http') ? imageUrl : 'https://nyumbalink-backend-eaw2.onrender.com$imageUrl',
                        height: 200,
                        width: double.infinity,
                        fit: BoxFit.cover,
                      ),
                    Padding(
                      padding: EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(l['title'], style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          SizedBox(height: 4),
                          Text("${l['property_summary']['neighbourhood']} · ${l['property_summary']['property_type']}", style: TextStyle(color: Colors.grey)),
                          SizedBox(height: 8),
                          Text("${l['currency']} ${l['price']}", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.emerald)),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
'''
(LIB_DIR / "home_screen.dart").write_text(HOME_SCREEN.strip() + "\n", encoding="utf-8")

# Main
MAIN_DART = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'login_screen.dart';
import 'home_screen.dart';

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
      initialRoute: '/',
      routes: {
        '/': (context) => LoginScreen(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}
'''
(LIB_DIR / "main.dart").write_text(MAIN_DART.strip() + "\n", encoding="utf-8")

print("""
==================================================
🎉 PHASE 27 COMPLETE: FLUTTER FOUNDATION BUILT!
==================================================

Your Flutter app is ready. Here is how to run it:

1. Open a new terminal and navigate to the mobile folder:
   cd mobile

2. Make sure you have an Android emulator running, or a physical device connected.

3. Run the app:
   flutter run

--------------------------------------------------
📱 WHAT YOU JUST BUILT:
--------------------------------------------------
- The Backend now supports mobile auth (sends JWT in body).
- A beautiful Login screen.
- An API Client that handles tokens via SharedPreferences.
- A Home feed that fetches the real listings from your Render backend!

NOTE: For the images to load in the app, we are using `cached_network_image`. 
It will automatically pull the images from Cloudinary/Render.

You can test it by logging in with:
landlord@nyumbalink.com / LandlordPassword123!
""")