#!/usr/bin/env python3
"""NyumbaLink Phase 27b: Flutter Search & Listing Detail Screen."""
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

  static Future<List<dynamic>> getListings({String? query}) async {
    String url = '$baseUrl/listings/';
    if (query != null && query.isNotEmpty) {
      url += '?search=$query';
    }
    final res = await http.get(Uri.parse(url), headers: await getHeaders());
    if (res.statusCode == 200) {
      return jsonDecode(res.body)['results'];
    }
    throw Exception('Failed to load listings');
  }

  static Future<Map<String, dynamic>> getListingDetail(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$id/'), headers: await getHeaders());
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    }
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
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('access_token', data['access']);
      return data['user'];
    }
    throw Exception('Invalid credentials');
  }
}
'''
(LIB / "api_client.dart").write_text(API_CLIENT.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 2. Create Listing Detail Screen
DETAIL_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';

class ListingDetailScreen extends StatefulWidget {
  final String listingId;

  ListingDetailScreen({required this.listingId});

  @override
  _ListingDetailScreenState createState() => _ListingDetailScreenState();
}

class _ListingDetailScreenState extends State<ListingDetailScreen> {
  late Future<Map<String, dynamic>> _listingFuture;

  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId);
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Property Details"),
        backgroundColor: Color(0xFF059669),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _listingFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text("Error loading property details"));
          }

          final listing = snapshot.data!;
          final mediaList = listing['media'] as List<dynamic>;
          final imageUrl = mediaList.isNotEmpty ? mediaList[0]['file'] : null;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Main Image
                if (imageUrl != null)
                  CachedNetworkImage(
                    imageUrl: _getFullImageUrl(imageUrl),
                    height: 300,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        listing['title'],
                        style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 8),
                      Text(
                        "${listing['property_summary']['neighbourhood']} · ${listing['property_summary']['property_type']}",
                        style: TextStyle(fontSize: 16, color: Colors.grey[600]),
                      ),
                      SizedBox(height: 16),
                      Text(
                        "${listing['currency']} ${listing['price']}",
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF059669)),
                      ),
                      Divider(height: 32),
                      Text(
                        "Description",
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 8),
                      Text(
                        listing['description'] ?? "No description provided.",
                        style: TextStyle(fontSize: 16, height: 1.5),
                      ),
                      Divider(height: 32),
                      // Contact Button
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: () {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text("Contact feature coming soon in the app!")),
                            );
                          },
                          icon: Icon(Icons.message),
                          label: Text("Contact Landlord"),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Color(0xFF059669),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
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

# ---------------------------------------------------------------- 3. Update Home Screen
HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';
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
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(30),
                  borderSide: BorderSide.none,
                ),
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
          if (listings.isEmpty) {
            return Center(child: Text("No properties found."));
          }

          return ListView.builder(
            itemCount: listings.length,
            itemBuilder: (context, index) {
              final l = listings[index];
              final imageUrl = l['media'].isNotEmpty ? l['media'][0]['file'] : null;
              
              return GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => ListingDetailScreen(listingId: l['id'])),
                  );
                },
                child: Card(
                  margin: EdgeInsets.all(8),
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (imageUrl != null)
                        CachedNetworkImage(
                          imageUrl: _getFullImageUrl(imageUrl),
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

print("""
==================================================
🎉 PHASE 27b COMPLETE: FLUTTER SEARCH & DETAILS!
==================================================

Go back to your terminal (in the `mobile` directory) and hot reload the app 
by pressing 'r' in the terminal (or restart it).

1. You will now see a Search Bar at the top of the Home screen.
2. Type "Kabulonga" and hit Enter to filter the listings.
3. Tap on any property card. It will open a beautiful, scrollable detail page 
   with the large image, price, and full description.
""")