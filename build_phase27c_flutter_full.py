#!/usr/bin/env python3
"""NyumbaLink Phase 27c: Public Home, Carousel, Register, and Mobile Chat."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. API Client
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

  static Future<void> setToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  static Future<Map<String, String>> getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<List<dynamic>> getListings({String? query}) async {
    String url = '$baseUrl/listings/';
    if (query != null && query.isNotEmpty) url += '?search=$query';
    
    final res = await http.get(Uri.parse(url), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load listings');
  }

  static Future<Map<String, dynamic>> getListingDetail(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$id/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load listing');
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      await setToken(data['access']);
      return data['user'];
    }
    throw Exception('Invalid credentials');
  }

  static Future<Map<String, dynamic>> register(String email, String password, String firstName) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/register/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password, 'first_name': firstName}),
    );
    if (res.statusCode == 201) {
      final data = jsonDecode(res.body);
      await setToken(data['access']);
      return data['user'];
    }
    throw Exception('Registration failed');
  }

  // --- Messaging ---
  static Future<String> startConversation(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/start/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    if (res.statusCode == 200) return jsonDecode(res.body)['id'];
    throw Exception('Failed to start chat');
  }

  static Future<List<dynamic>> getMessages(String conversationId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
    );
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load messages');
  }

  static Future<void> sendMessage(String conversationId, String body) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
      body: jsonEncode({'body': body}),
    );
    if (res.statusCode != 201) throw Exception('Failed to send message');
  }
}
'''
(LIB / "api_client.dart").write_text(API_CLIENT.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 2. Auth Provider
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

  Future<void> register(String email, String password, String firstName) async {
    _user = await ApiClient.register(email, password, firstName);
    notifyListeners();
  }

  Future<void> logout() async {
    await ApiClient.clearToken();
    _user = null;
    notifyListeners();
  }
}
'''
(LIB / "auth_provider.dart").write_text(AUTH_PROVIDER.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 3. Register Screen
REGISTER_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';

class RegisterScreen extends StatefulWidget {
  @override
  _RegisterScreenState createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  bool _loading = false;

  void _submit() async {
    setState(() => _loading = true);
    try {
      await Provider.of<AuthProvider>(context, listen: false)
          .register(_emailCtrl.text, _passCtrl.text, _nameCtrl.text);
      Navigator.pop(context); // Go back to home after registering
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Create Account"), backgroundColor: Color(0xFF059669)),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(controller: _nameCtrl, decoration: InputDecoration(labelText: 'First Name', border: OutlineInputBorder())),
            SizedBox(height: 16),
            TextField(controller: _emailCtrl, decoration: InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
            SizedBox(height: 16),
            TextField(controller: _passCtrl, decoration: InputDecoration(labelText: 'Password', border: OutlineInputBorder()), obscureText: true),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _loading ? null : _submit,
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Sign Up"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
'''
(LIB / "register_screen.dart").write_text(REGISTER_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 4. Chat Screen
CHAT_SCREEN = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class ChatScreen extends StatefulWidget {
  final String conversationId;
  final String landlordName;

  ChatScreen({required this.conversationId, required this.landlordName});

  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late Future<List<dynamic>> _messagesFuture;
  final _msgCtrl = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  void _loadMessages() {
    setState(() {
      _messagesFuture = ApiClient.getMessages(widget.conversationId);
    });
  }

  void _send() async {
    if (_msgCtrl.text.trim().isEmpty) return;
    setState(() => _sending = true);
    try {
      await ApiClient.sendMessage(widget.conversationId, _msgCtrl.text);
      _msgCtrl.clear();
      _loadMessages();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to send")));
    }
    setState(() => _sending = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.landlordName), backgroundColor: Color(0xFF059669)),
      body: Column(
        children: [
          Expanded(
            child: FutureBuilder<List<dynamic>>(
              future: _messagesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
                if (snapshot.hasError) return Center(child: Text("Error loading messages"));
                
                final msgs = snapshot.data!;
                return ListView.builder(
                  padding: EdgeInsets.all(16),
                  itemCount: msgs.length,
                  itemBuilder: (context, index) {
                    final m = msgs[index];
                    return Align(
                      alignment: Alignment.centerLeft, // Simplified for now; you'd check sender ID to align right
                      child: Container(
                        margin: EdgeInsets.only(bottom: 8),
                        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.grey[200],
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(m['body'] ?? ''),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _msgCtrl,
                    decoration: InputDecoration(
                      hintText: "Type a message...",
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                      contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send, color: Color(0xFF059669)),
                  onPressed: _sending ? null : _send,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
'''
(LIB / "chat_screen.dart").write_text(CHAT_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 5. Detail Screen (with Carousel and Chat)
DETAIL_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'chat_screen.dart';
import 'login_screen.dart';

class ListingDetailScreen extends StatefulWidget {
  final String listingId;

  ListingDetailScreen({required this.listingId});

  @override
  _ListingDetailScreenState createState() => _ListingDetailScreenState();
}

class _ListingDetailScreenState extends State<ListingDetailScreen> {
  late Future<Map<String, dynamic>> _listingFuture;
  bool _startingChat = false;

  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId);
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  void _startChat(String listingId, String landlordName) async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    if (auth.user == null) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen()));
      return;
    }

    setState(() => _startingChat = true);
    try {
      final convId = await ApiClient.startConversation(listingId);
      Navigator.push(context, MaterialPageRoute(
        builder: (_) => ChatScreen(conversationId: convId, landlordName: landlordName),
      ));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to open chat")));
    }
    setState(() => _startingChat = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Property Details"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _listingFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading property details"));

          final listing = snapshot.data!;
          final mediaList = listing['media'] as List<dynamic>;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Image Carousel
                if (mediaList.isNotEmpty)
                  SizedBox(
                    height: 300,
                    child: PageView.builder(
                      itemCount: mediaList.length,
                      itemBuilder: (context, index) {
                        return CachedNetworkImage(
                          imageUrl: _getFullImageUrl(mediaList[index]['file']),
                          width: double.infinity,
                          fit: BoxFit.cover,
                        );
                      },
                    ),
                  ),
                
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(listing['title'], style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      Text("${listing['property_summary']['neighbourhood']} · ${listing['property_summary']['property_type']}", style: TextStyle(fontSize: 16, color: Colors.grey[600])),
                      SizedBox(height: 16),
                      Text("${listing['currency']} ${listing['price']}", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                      Divider(height: 32),
                      Text("Description", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      Text(listing['description'] ?? "No description provided.", style: TextStyle(fontSize: 16, height: 1.5)),
                      Divider(height: 32),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                          icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                          label: Text(_startingChat ? "Opening..." : "Message Landlord"),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Color(0xFF059669),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
'''
(LIB / "listing_detail_screen.dart").write_text(DETAIL_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 6. Home Screen (Public Access)
HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'login_screen.dart';
import 'register_screen.dart';
import 'listing_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _listings;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _listings = ApiClient.getListings();
  }

  void _performSearch(String query) {
    setState(() {
      _listings = ApiClient.getListings(query: query);
    });
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    
    return Scaffold(
      appBar: AppBar(
        title: Text("NyumbaLink"),
        backgroundColor: Color(0xFF059669),
        actions: [
          if (auth.user == null) ...[
            TextButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
              child: Text("Login", style: TextStyle(color: Colors.white)),
            ),
            TextButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => RegisterScreen())),
              child: Text("Register", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          ] else ...[
            IconButton(
              icon: Icon(Icons.logout, color: Colors.white),
              onPressed: () => auth.logout(),
            ),
          ]
        ],
        bottom: PreferredSize(
          preferredSize: Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: TextField(
              controller: _searchController,
              onSubmitted: _performSearch,
              decoration: InputDecoration(
                hintText: 'Search by neighbourhood...',
                filled: true,
                fillColor: Colors.white,
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none),
                contentPadding: EdgeInsets.symmetric(vertical: 0),
              ),
            ),
          ),
        ),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _listings,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings"));
          
          final listings = snapshot.data!;
          if (listings.isEmpty) return Center(child: Text("No properties found."));

          return ListView.builder(
            itemCount: listings.length,
            itemBuilder: (context, index) {
              final l = listings[index];
              final imageUrl = l['media'].isNotEmpty ? l['media'][0]['file'] : null;
              
              return GestureDetector(
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: l['id']))),
                child: Card(
                  margin: EdgeInsets.all(8),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (imageUrl != null)
                        CachedNetworkImage(imageUrl: _getFullImageUrl(imageUrl), height: 200, width: double.infinity, fit: BoxFit.cover),
                      Padding(
                        padding: EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(l['title'], style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            SizedBox(height: 4),
                            Text("${l['property_summary']['neighbourhood']} · ${l['property_summary']['property_type']}", style: TextStyle(color: Colors.grey)),
                            SizedBox(height: 8),
                            Text("${l['currency']} ${l['price']}", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                          ],
                        ),
                      ),
                    ],
                  ),
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
(LIB / "home_screen.dart").write_text(HOME_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 7. Update main.dart
MAIN_DART = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
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
      home: HomeScreen(), // Changed: Home is the first screen now
    );
  }
}
'''
(LIB / "main.dart").write_text(MAIN_DART.strip() + "\n", encoding="utf-8")

print("""
==================================================
🎉 PHASE 27c COMPLETE: PUBLIC APP + CHAT + CAROUSEL
==================================================

Go back to your Flutter terminal and press 'r' to hot reload (or restart it).

Here is what is new:
1. **Public Access**: You land on the Home Page immediately. Login and Register buttons are in the top bar.
2. **Image Carousel**: Open any property and swipe left/right to see all photos.
3. **Registration**: You can create a new account from the app.
4. **Real Chat**: Click "Message Landlord". It will start a real conversation in your database and open a chat screen where you can send messages back and forth.
""")