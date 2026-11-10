#!/usr/bin/env python3
"""NyumbaLink Phase 40: Mobile Landlord Profiles & Reviews."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getPublicProfile" not in text:
    new_methods = '''
  // --- Profiles & Reviews ---
  static Future<Map<String, dynamic>> getPublicProfile(String userId) async {
    final res = await http.get(Uri.parse('$baseUrl/profiles/$userId/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load profile');
  }

  static Future<void> submitReview(String userId, int rating, String comment) async {
    final res = await http.post(
      Uri.parse('$baseUrl/profiles/$userId/reviews/'),
      headers: await getHeaders(),
      body: jsonEncode({'rating': rating, 'comment': comment}),
    );
    if (res.statusCode != 201) {
      final error = jsonDecode(res.body);
      throw Exception(error.values.first[0] ?? 'Failed to submit review');
    }
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added profile and review methods")

# ----------------------------------------------------------------
# 2. Flutter: Create Landlord Profile Screen
# ----------------------------------------------------------------
PROFILE_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'listing_detail_screen.dart';

class LandlordProfileScreen extends StatefulWidget {
  final String landlordId;
  final String landlordEmail;

  LandlordProfileScreen({required this.landlordId, required this.landlordEmail});

  @override
  _LandlordProfileScreenState createState() => _LandlordProfileScreenState();
}

class _LandlordProfileScreenState extends State<LandlordProfileScreen> {
  late Future<Map<String, dynamic>> _profileFuture;
  bool _submittingReview = false;

  @override
  void initState() {
    super.initState();
    _profileFuture = ApiClient.getPublicProfile(widget.landlordId);
  }

  String _getFullImageUrl(String? url) {
    if (url == null || url.isEmpty) return '';
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  void _showReviewDialog() {
    int rating = 5;
    final commentCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setStateDialog) {
          return AlertDialog(
            title: Text("Leave a Review"),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(5, (index) {
                    return IconButton(
                      icon: Icon(index < rating ? Icons.star : Icons.star_border, color: Colors.orange),
                      onPressed: () => setStateDialog(() => rating = index + 1),
                    );
                  }),
                ),
                TextField(
                  controller: commentCtrl,
                  decoration: InputDecoration(hintText: "Share your experience...", border: OutlineInputBorder()),
                  maxLines: 3,
                ),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: Text("Cancel")),
              ElevatedButton(
                onPressed: _submittingReview ? null : () async {
                  if (commentCtrl.text.trim().isEmpty) return;
                  setState(() => _submittingReview = true);
                  Navigator.pop(context);
                  try {
                    await ApiClient.submitReview(widget.landlordId, rating, commentCtrl.text);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Review submitted!")));
                      setState(() { _profileFuture = ApiClient.getPublicProfile(widget.landlordId); });
                    }
                  } catch (e) {
                    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                  if (mounted) setState(() => _submittingReview = false);
                },
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: Text("Submit"),
              )
            ],
          );
        }
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(title: Text("Landlord Profile"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading profile"));

          final profile = snapshot.data!;
          final listings = profile['listings'] as List<dynamic>? ?? [];
          final reviews = profile['reviews'] as List<dynamic>? ?? [];
          final isOwnProfile = auth.user?['id'] == widget.landlordId;
          final hasReviewed = reviews.any((r) => r['reviewer'] == auth.user?['id']);
          
          final avatarUrl = _getFullImageUrl(profile['avatar']);
          final coverUrl = _getFullImageUrl(profile['cover_photo']);

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Cover Photo
                Container(
                  height: 150,
                  width: double.infinity,
                  color: Color(0xFF059669),
                  child: coverUrl.isNotEmpty 
                    ? CachedNetworkImage(imageUrl: coverUrl, fit: BoxFit.cover)
                    : null,
                ),
                
                // Avatar & Info
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Transform.translate(
                    offset: Offset(0, -40),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        CircleAvatar(
                          radius: 45,
                          backgroundColor: Colors.white,
                          child: CircleAvatar(
                            radius: 42,
                            backgroundColor: Color(0xFF059669),
                            backgroundImage: avatarUrl.isNotEmpty ? CachedNetworkImageProvider(avatarUrl) : null,
                            child: avatarUrl.isEmpty 
                              ? Text((profile['first_name'] ?? 'L')[0].toUpperCase(), style: TextStyle(fontSize: 32, color: Colors.white))
                              : null,
                          ),
                        ),
                        SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "${profile['first_name'] ?? 'Landlord'} ${profile['last_name'] ?? ''}".trim(), 
                                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)
                              ),
                              Text(profile['email'] ?? '', style: TextStyle(color: Colors.grey[600], fontSize: 14)),
                            ],
                          ),
                        )
                      ],
                    ),
                  ),
                ),

                // Verification & Stats
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (profile['verification_status']?['identity'] == true)
                        Container(
                          margin: EdgeInsets.only(bottom: 16),
                          padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(color: Colors.blue[50], borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.blue)),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.verified, color: Colors.blue, size: 16),
                              SizedBox(width: 4),
                              Text("ID Verified", style: TextStyle(color: Colors.blue[800], fontWeight: FontWeight.bold, fontSize: 12)),
                            ],
                          ),
                        ),
                        
                      if (profile['bio'] != null && profile['bio'].toString().isNotEmpty)
                        Padding(
                          padding: EdgeInsets.only(bottom: 24),
                          child: Text(profile['bio'], style: TextStyle(fontSize: 15, height: 1.5)),
                        ),

                      Text("Properties (${listings.length})", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      SizedBox(height: 12),
                      
                      // Listings Horizontal Scroll
                      if (listings.isEmpty)
                        Text("No active listings.", style: TextStyle(color: Colors.grey))
                      else
                        SizedBox(
                          height: 200,
                          child: ListView.builder(
                            scrollDirection: Axis.horizontal,
                            itemCount: listings.length,
                            itemBuilder: (context, index) {
                              final l = listings[index];
                              final img = l['media'].isNotEmpty ? l['media'][0]['file'] : null;
                              return GestureDetector(
                                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: l['id']))),
                                child: Container(
                                  width: 160,
                                  margin: EdgeInsets.only(right: 12),
                                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8), boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4)]),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      ClipRRect(
                                        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
                                        child: img != null 
                                          ? CachedNetworkImage(imageUrl: _getFullImageUrl(img), height: 100, width: 160, fit: BoxFit.cover)
                                          : Container(height: 100, color: Colors.grey[200], child: Icon(Icons.home)),
                                      ),
                                      Padding(
                                        padding: EdgeInsets.all(8),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(l['title'], maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.bold)),
                                            SizedBox(height: 4),
                                            Text("${l['currency']} ${l['price']}", style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold, fontSize: 12)),
                                          ],
                                        ),
                                      )
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),

                      Divider(height: 48),
                      
                      // Reviews Section
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Reviews (${reviews.length})", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          if (auth.user != null && !isOwnProfile && !hasReviewed)
                            TextButton(
                              onPressed: _showReviewDialog,
                              child: Text("Leave Review"),
                            )
                        ],
                      ),
                      SizedBox(height: 12),
                      
                      if (reviews.isEmpty)
                        Text("No reviews yet.", style: TextStyle(color: Colors.grey))
                      else
                        ...reviews.map((r) => Card(
                          margin: EdgeInsets.only(bottom: 8),
                          child: Padding(
                            padding: EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(r['reviewer_name'] ?? r['reviewer_email'].split('@')[0], style: TextStyle(fontWeight: FontWeight.bold)),
                                    Row(
                                      children: List.generate(5, (i) => Icon(i < r['rating'] ? Icons.star : Icons.star_border, color: Colors.orange, size: 16)),
                                    )
                                  ],
                                ),
                                SizedBox(height: 8),
                                Text(r['comment'], style: TextStyle(color: Colors.grey[800])),
                              ],
                            ),
                          ),
                        )),
                      
                      SizedBox(height: 40),
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
(LIB / "landlord_profile_screen.dart").write_text(PROFILE_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created landlord_profile_screen.dart")

# ----------------------------------------------------------------
# 3. Flutter: Link to Profile from Listing Detail
# ----------------------------------------------------------------
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "LandlordProfileScreen" not in text:
    text = text.replace(
        "import 'login_screen.dart';",
        "import 'login_screen.dart';\nimport 'landlord_profile_screen.dart';"
    )
    
    # Add a clickable "View Profile" row above the buttons
    old_layout = '''                      Divider(height: 32),
                      
                      if (auth.user == null)'''
    
    new_layout = '''                      Divider(height: 32),

                      // Landlord Info Row
                      GestureDetector(
                        onTap: () {
                          Navigator.push(context, MaterialPageRoute(
                            builder: (_) => LandlordProfileScreen(
                              landlordId: listing['created_by'],
                              landlordEmail: listing['created_by_email'] ?? '',
                            )
                          ));
                        },
                        child: Container(
                          padding: EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.grey[50], borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey[300]!)),
                          child: Row(
                            children: [
                              CircleAvatar(backgroundColor: Color(0xFF059669), child: Icon(Icons.person, color: Colors.white)),
                              SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text("Advertised by", style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                                    Text(listing['created_by_email'] ?? 'Landlord', style: TextStyle(fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                              Icon(Icons.chevron_right, color: Colors.grey),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(height: 24),
                      
                      if (auth.user == null)'''
                      
    text = text.replace(old_layout, new_layout)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added link to Landlord Profile")

print("""
==================================================
🎉 PHASE 40 COMPLETE: MOBILE PROFILES & REVIEWS
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. Open a property. Scroll down past the description.
2. You will see a new "Advertised by [Landlord]" card. Click it.
3. This opens the Landlord's public profile showing their bio, verification badge, and other listings.
4. Scroll down to the Reviews section. Click "Leave Review", select stars, and write a comment.
5. Submit it. It will appear instantly!
""")