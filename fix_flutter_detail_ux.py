#!/usr/bin/env python3
"""Fixes the Flutter detail screen: Auth button visibility and Image Carousel dots."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

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
  int _currentImageIndex = 0; // Tracks the active image in the carousel

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
                // --- IMAGE CAROUSEL WITH DOTS ---
                if (mediaList.isNotEmpty)
                  Stack(
                    children: [
                      SizedBox(
                        height: 300,
                        child: PageView.builder(
                          onPageChanged: (index) {
                            setState(() => _currentImageIndex = index);
                          },
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
                      // Dots Indicator (Only show if more than 1 image)
                      if (mediaList.length > 1)
                        Positioned(
                          bottom: 12,
                          left: 0,
                          right: 0,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: List.generate(mediaList.length, (index) {
                              return AnimatedContainer(
                                duration: Duration(milliseconds: 300),
                                margin: EdgeInsets.symmetric(horizontal: 4),
                                width: _currentImageIndex == index ? 20 : 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: _currentImageIndex == index ? Color(0xFF059669) : Colors.white.withOpacity(0.6),
                                  borderRadius: BorderRadius.circular(4),
                                ),
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
                      
                      // --- DYNAMIC BUTTON (LOGIN VS MESSAGE) ---
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: auth.user == null 
                          ? ElevatedButton.icon(
                              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                              icon: Icon(Icons.lock_outline),
                              label: Text("Log in to Contact Landlord"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.grey[800],
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                              ),
                            )
                          : ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat 
                                ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) 
                                : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
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

print("""
==================================================
🎉 DETAIL SCREEN FIXED: CAROUSEL DOTS & AUTH BUTTON
==================================================

Because this changes the stateful layout, you must **fully restart** the app 
(hot reload might not catch structural changes).

In your Flutter terminal:
  1. Press 'q' to quit.
  2. Run: flutter run -d chrome --web-port 5173

Now, if you are logged out, the button will say "Log in to Contact".
If you are logged in, the image carousel will have animated dots at the bottom, 
and you can swipe left/right through all the photos.
""")