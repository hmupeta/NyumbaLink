#!/usr/bin/env python3
"""NyumbaLink Phase 28: Flutter Bottom Navigation, Saved, Inbox, and Profile."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Update API Client
API_CLIENT = '''
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http_parser/http_parser.dart';

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

  // --- Saved Properties ---
  static Future<List<dynamic>> getSavedListings() async {
    final res = await http.get(Uri.parse('$baseUrl/saved-listings/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load saved listings');
  }

  static Future<void> toggleSaveListing(String listingId, bool isSaved) async {
    if (isSaved) {
      await http.delete(Uri.parse('$baseUrl/saved-listings/$listingId/'), headers: await getHeaders());
    } else {
      await http.post(
        Uri.parse('$baseUrl/saved-listings/'),
        headers: await getHeaders(),
        body: jsonEncode({'listing_id': listingId}),
      );
    }
  }

  // --- Messaging ---
  static Future<List<dynamic>> getConversations() async {
    final res = await http.get(Uri.parse('$baseUrl/conversations/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load conversations');
  }

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

  static Future<void> sendFileMessage(String conversationId, List<int> fileBytes, String fileName, String type) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
    );
    final token = await getToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    request.fields['body'] = type == 'AUDIO' ? 'Voice Note' : 'Attachment';
    request.fields['message_type'] = type;
    request.files.add(http.MultipartFile.fromBytes(
      'file', fileBytes, filename: fileName,
      contentType: type == 'AUDIO' ? MediaType('audio', 'mp4') : null,
    ));
    final response = await request.send();
    if (response.statusCode != 201) throw Exception('Failed to send file');
  }

  static Future<void> reactToMessage(String conversationId, String messageId, String emoji) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/$messageId/react/'),
      headers: await getHeaders(),
      body: jsonEncode({'emoji': emoji}),
    );
    if (res.statusCode != 200) throw Exception('Failed to react');
  }
}
'''
(LIB / "api_client.dart").write_text(API_CLIENT.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 2. Inbox Screen
INBOX_SCREEN = '''
import 'package:flutter/material.dart';
import 'api_client.dart';
import 'chat_screen.dart';

class InboxScreen extends StatefulWidget {
  @override
  _InboxScreenState createState() => _InboxScreenState();
}

class _InboxScreenState extends State<InboxScreen> {
  late Future<List<dynamic>> _convsFuture;

  @override
  void initState() {
    super.initState();
    _convsFuture = ApiClient.getConversations();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Inbox"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _convsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading inbox. Please log in."));
          
          final convs = snapshot.data!;
          if (convs.isEmpty) return Center(child: Text("No messages yet."));

          return ListView.builder(
            itemCount: convs.length,
            itemBuilder: (context, index) {
              final c = convs[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Color(0xFF059669),
                  child: Icon(Icons.home, color: Colors.white),
                ),
                title: Text(c['listing_title'], maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text(c['last_message'] != null ? c['last_message']['body'] : 'No messages', maxLines: 1, overflow: TextOverflow.ellipsis),
                trailing: Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => ChatScreen(
                      conversationId: c['id'],
                      landlordName: c['landlord_email'] == c['landlord'] ? c['seeker_email'] : c['landlord_email'],
                    )),
                  ).then((_) => setState(() { _convsFuture = ApiClient.getConversations(); }));
                },
              );
            },
          );
        },
      ),
    );
  }
}
'''
(LIB / "inbox_screen.dart").write_text(INBOX_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 3. Saved Screen
SAVED_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';
import 'listing_detail_screen.dart';

class SavedScreen extends StatefulWidget {
  @override
  _SavedScreenState createState() => _SavedScreenState();
}

class _SavedScreenState extends State<SavedScreen> {
  late Future<List<dynamic>> _savedFuture;

  @override
  void initState() {
    super.initState();
    _savedFuture = ApiClient.getSavedListings();
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Saved Properties"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _savedFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading saved properties. Please log in."));
          
          final savedItems = snapshot.data!;
          if (savedItems.isEmpty) return Center(child: Text("No saved properties yet."));

          return ListView.builder(
            itemCount: savedItems.length,
            itemBuilder: (context, index) {
              final listing = savedItems[index]['listing'];
              final imageUrl = listing['media'].isNotEmpty ? listing['media'][0]['file'] : null;

              return GestureDetector(
                onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: listing['id'])))
                  .then((_) => setState(() { _savedFuture = ApiClient.getSavedListings(); }));
                },
                child: Card(
                  margin: EdgeInsets.all(8),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (imageUrl != null)
                        CachedNetworkImage(imageUrl: _getFullImageUrl(imageUrl), height: 150, width: double.infinity, fit: BoxFit.cover),
                      Padding(
                        padding: EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(listing['title'], style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                            SizedBox(height: 4),
                            Text("${listing['currency']} ${listing['price']}", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF059669))),
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
(LIB / "saved_screen.dart").write_text(SAVED_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 4. Profile Screen
PROFILE_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'login_screen.dart';

class ProfileScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(title: Text("My Profile"), backgroundColor: Color(0xFF059669)),
      body: auth.user == null
        ? Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text("You are not logged in."),
                SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                  child: Text("Log In"),
                  style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                )
              ],
            ),
          )
        : Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: Color(0xFF059669),
                  child: Text(
                    auth.user!['first_name']?.isNotEmpty == true ? auth.user!['first_name'][0].toUpperCase() : 'U',
                    style: TextStyle(fontSize: 32, color: Colors.white),
                  ),
                ),
                SizedBox(height: 16),
                Text("${auth.user!['first_name']} ${auth.user!['last_name'] ?? ''}", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                Text(auth.user!['email'], style: TextStyle(color: Colors.grey)),
                Divider(height: 40),
                ListTile(
                  leading: Icon(Icons.dashboard, color: Color(0xFF059669)),
                  title: Text("Landlord Dashboard"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    // Note: In a real app, you would navigate to a WebView or a dedicated mobile dashboard
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Dashboard coming in Phase 29!")));
                  },
                ),
                ListTile(
                  leading: Icon(Icons.logout, color: Colors.red),
                  title: Text("Logout", style: TextStyle(color: Colors.red)),
                  onTap: () {
                    auth.logout();
                  },
                ),
              ],
            ),
          ),
    );
  }
}
'''
(LIB / "profile_screen.dart").write_text(PROFILE_SCREEN.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 5. Main Layout (Bottom Nav)
MAIN_LAYOUT = '''
import 'package:flutter/material.dart';
import 'home_screen.dart';
import 'saved_screen.dart';
import 'inbox_screen.dart';
import 'profile_screen.dart';

class MainLayout extends StatefulWidget {
  @override
  _MainLayoutState createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _currentIndex = 0;
  final List<Widget> _screens = [
    HomeScreen(),
    SavedScreen(),
    InboxScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() { _currentIndex = index; });
        },
        selectedItemColor: Color(0xFF059669),
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        items: [
          BottomNavigationBarItem(icon: Icon(Icons.explore), label: 'Explore'),
          BottomNavigationBarItem(icon: Icon(Icons.favorite), label: 'Saved'),
          BottomNavigationBarItem(icon: Icon(Icons.message), label: 'Inbox'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
'''
(LIB / "main_layout.dart").write_text(MAIN_LAYOUT.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 6. Update Main.dart
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
      home: MainLayout(), // Swapped to MainLayout with Bottom Nav
    );
  }
}
'''
(LIB / "main.dart").write_text(MAIN_DART.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 7. Update Home Screen (Remove Auth Buttons)
HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
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
    return Scaffold(
      appBar: AppBar(
        title: Text("NyumbaLink"),
        backgroundColor: Color(0xFF059669),
        automaticallyImplyLeading: false,
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

# ---------------------------------------------------------------- 8. Update Detail Screen (Add Heart Icon)
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
  bool _isSaved = false;
  bool _saving = false;
  int _currentImageIndex = 0;

  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId).then((data) {
      setState(() { _isSaved = data['is_saved'] ?? false; });
      return data;
    });
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  void _toggleSave() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await ApiClient.toggleSaveListing(widget.listingId, _isSaved);
      setState(() => _isSaved = !_isSaved);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_isSaved ? "Saved!" : "Removed from saved")));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to save. Please log in.")));
    }
    setState(() => _saving = false);
  }

  void _startChat(String listingId, String landlordName) async {
    setState(() => _startingChat = true);
    try {
      final convId = await ApiClient.startConversation(listingId);
      Navigator.push(context, MaterialPageRoute(
        builder: (_) => ChatScreen(conversationId: convId, landlordName: landlordName),
      ));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to open chat. Please log in again.")));
    }
    setState(() => _startingChat = false);
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text("Property Details"), 
        backgroundColor: Color(0xFF059669),
        actions: [
          IconButton(
            icon: Icon(_isSaved ? Icons.favorite : Icons.favorite_border, color: _isSaved ? Colors.red : Colors.white),
            onPressed: auth.user == null ? null : _toggleSave,
          )
        ],
      ),
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
                if (mediaList.isNotEmpty)
                  Stack(
                    children: [
                      SizedBox(
                        height: 300,
                        child: PageView.builder(
                          onPageChanged: (index) => setState(() => _currentImageIndex = index),
                          itemCount: mediaList.length,
                          itemBuilder: (context, index) => CachedNetworkImage(imageUrl: _getFullImageUrl(mediaList[index]['file']), width: double.infinity, fit: BoxFit.cover),
                        ),
                      ),
                      if (mediaList.length > 1)
                        Positioned(
                          bottom: 12, left: 0, right: 0,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: List.generate(mediaList.length, (index) {
                              return AnimatedContainer(
                                duration: Duration(milliseconds: 300),
                                margin: EdgeInsets.symmetric(horizontal: 4),
                                width: _currentImageIndex == index ? 20 : 8,
                                height: 8,
                                decoration: BoxDecoration(color: _currentImageIndex == index ? Color(0xFF059669) : Colors.white.withOpacity(0.6), borderRadius: BorderRadius.circular(4)),
                              );
                            }),
                          ),
                        ),
                    ],
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
                        child: auth.user == null 
                          ? ElevatedButton.icon(
                              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                              icon: Icon(Icons.lock_outline),
                              label: Text("Log in to Contact Landlord"),
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.grey[800], shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                            )
                          : ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
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

print("""
==================================================
🎉 PHASE 28 COMPLETE: BOTTOM NAV, SAVED, INBOX, PROFILE
==================================================

Go back to your terminal, quit ('q'), and restart the app.

Here is what is new:
1. **Bottom Navigation Bar**: You can now switch between Explore, Saved, Inbox, and Profile.
2. **Saved Properties**: Tap the Heart icon on any property detail screen. It will save to your account and appear in the "Saved" tab.
3. **Inbox**: View all your chat conversations in one list.
4. **Profile**: View your account details and log out.

*(Note: You must be logged in for Saved and Inbox to work).*
""")