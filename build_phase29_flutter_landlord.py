#!/usr/bin/env python3
"""NyumbaLink Phase 29: Flutter Landlord Dashboard & Create Listing."""
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

  // --- Landlord Features ---
  static Future<List<dynamic>> getMyListings() async {
    final res = await http.get(Uri.parse('$baseUrl/listings/my_listings/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load your listings');
  }

  static Future<List<dynamic>> getNeighbourhoods() async {
    final res = await http.get(Uri.parse('$baseUrl/neighbourhoods/?page=1'));
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load locations');
  }

  static Future<void> createPropertyAndListing({
    required String title,
    required String description,
    required double price,
    required int bedrooms,
    required int bathrooms,
    required double floorArea,
    required String propertyType,
    required String neighbourhoodId,
    required List<int> imageBytes,
    required String imageName,
  }) async {
    // 1. Create Property
    final propRes = await http.post(
      Uri.parse('$baseUrl/properties/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'neighbourhood': neighbourhoodId,
        'property_type': propertyType,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'floor_area': floorArea,
        'description': description,
      }),
    );
    if (propRes.statusCode != 201) throw Exception('Failed to create property');
    final propId = jsonDecode(propRes.body)['id'];

    // 2. Create Listing
    final listRes = await http.post(
      Uri.parse('$baseUrl/listings/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'property': propId,
        'transaction_type': 'RENT',
        'price': price,
        'currency': 'ZMW',
        'title': title,
        'description': description,
      }),
    );
    if (listRes.statusCode != 201) throw Exception('Failed to create listing');
    final listingId = jsonDecode(listRes.body)['id'];

    // 3. Upload Image
    if (imageBytes.isNotEmpty) {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/listings/$listingId/media/'),
      );
      final token = await getToken();
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      
      request.files.add(http.MultipartFile.fromBytes('file', imageBytes, filename: imageName));
      request.fields['media_type'] = 'IMAGE';
      
      final mediaRes = await request.send();
      if (mediaRes.statusCode != 201) throw Exception('Listing created, but image upload failed');
    }
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

# ---------------------------------------------------------------- 2. Landlord Dashboard Screen
LANDLORD_DASHBOARD = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';
import 'create_listing_screen.dart';

class LandlordDashboardScreen extends StatefulWidget {
  @override
  _LandlordDashboardScreenState createState() => _LandlordDashboardScreenState();
}

class _LandlordDashboardScreenState extends State<LandlordDashboardScreen> {
  late Future<List<dynamic>> _listingsFuture;

  @override
  void initState() {
    super.initState();
    _loadListings();
  }

  void _loadListings() {
    setState(() {
      _listingsFuture = ApiClient.getMyListings();
    });
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("My Properties"), backgroundColor: Color(0xFF059669)),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(context, MaterialPageRoute(builder: (_) => CreateListingScreen()))
            .then((_) => _loadListings()); // Refresh list when returning
        },
        backgroundColor: Color(0xFF059669),
        child: Icon(Icons.add, color: Colors.white),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _listingsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading your properties."));
          
          final listings = snapshot.data!;
          if (listings.isEmpty) return Center(child: Text("You haven't listed any properties yet."));

          return ListView.builder(
            padding: EdgeInsets.all(8),
            itemCount: listings.length,
            itemBuilder: (context, index) {
              final l = listings[index];
              final imageUrl = l['media'].isNotEmpty ? l['media'][0]['file'] : null;
              
              return Card(
                clipBehavior: Clip.antiAlias,
                child: ListTile(
                  contentPadding: EdgeInsets.all(8),
                  leading: Container(
                    width: 80, height: 80,
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(8), color: Colors.grey[200]),
                    child: imageUrl != null 
                      ? CachedNetworkImage(imageUrl: _getFullImageUrl(imageUrl), fit: BoxFit.cover)
                      : Icon(Icons.home, color: Colors.grey),
                  ),
                  title: Text(l['title'], maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(height: 4),
                      Text("${l['currency']} ${l['price']}", style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                      SizedBox(height: 4),
                      Container(
                        padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: l['status'] == 'PUBLISHED' ? Colors.green[100] : Colors.orange[100],
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(l['status'], style: TextStyle(
                          fontSize: 10, 
                          color: l['status'] == 'PUBLISHED' ? Colors.green[800] : Colors.orange[800],
                          fontWeight: FontWeight.bold
                        )),
                      )
                    ],
                  ),
                  trailing: Icon(Icons.chevron_right),
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
(LIB / "landlord_dashboard_screen.dart").write_text(LANDLORD_DASHBOARD.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 3. Create Listing Screen
CREATE_LISTING = '''
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'api_client.dart';

class CreateListingScreen extends StatefulWidget {
  @override
  _CreateListingScreenState createState() => _CreateListingScreenState();
}

class _CreateListingScreenState extends State<CreateListingScreen> {
  final _titleCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _bedCtrl = TextEditingController();
  final _bathCtrl = TextEditingController();
  final _areaCtrl = TextEditingController();
  
  String _propertyType = 'HOUSE';
  String? _neighbourhoodId;
  List<dynamic> _neighbourhoods = [];
  List<int>? _imageBytes;
  String? _imageName;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadNeighbourhoods();
  }

  Future<void> _loadNeighbourhoods() async {
    try {
      final data = await ApiClient.getNeighbourhoods();
      setState(() { _neighbourhoods = data; });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to load locations")));
    }
  }

  void _pickImage() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
    if (result != null) {
      setState(() {
        _imageBytes = result.files.single.bytes;
        _imageName = result.files.single.name;
      });
    }
  }

  void _submit() async {
    if (_imageBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please select a cover image")));
      return;
    }
    if (_neighbourhoodId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please select a neighbourhood")));
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ApiClient.createPropertyAndListing(
        title: _titleCtrl.text,
        description: _descCtrl.text,
        price: double.parse(_priceCtrl.text),
        bedrooms: int.parse(_bedCtrl.text),
        bathrooms: int.parse(_bathCtrl.text),
        floorArea: double.parse(_areaCtrl.text),
        propertyType: _propertyType,
        neighbourhoodId: _neighbourhoodId!,
        imageBytes: _imageBytes!,
        imageName: _imageName!,
      );
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Property Listed Successfully!")));
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Create Listing"), backgroundColor: Color(0xFF059669)),
      body: _isLoading 
        ? Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(controller: _titleCtrl, decoration: InputDecoration(labelText: 'Listing Title', border: OutlineInputBorder())),
                SizedBox(height: 12),
                TextField(controller: _priceCtrl, decoration: InputDecoration(labelText: 'Monthly Rent (ZMW)', border: OutlineInputBorder()), keyboardType: TextInputType.number),
                SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _propertyType,
                  decoration: InputDecoration(labelText: 'Property Type', border: OutlineInputBorder()),
                  items: ['HOUSE', 'APARTMENT', 'TOWNHOUSE', 'LAND'].map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (val) => setState(() => _propertyType = val!),
                ),
                SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _neighbourhoodId,
                  decoration: InputDecoration(labelText: 'Neighbourhood', border: OutlineInputBorder()),
                  items: _neighbourhoods.map((n) => DropdownMenuItem(value: n['id'] as String, child: Text(n['name'] as String))).toList(),
                  onChanged: (val) => setState(() => _neighbourhoodId = val),
                ),
                SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: TextField(controller: _bedCtrl, decoration: InputDecoration(labelText: 'Beds', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                    SizedBox(width: 8),
                    Expanded(child: TextField(controller: _bathCtrl, decoration: InputDecoration(labelText: 'Baths', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                    SizedBox(width: 8),
                    Expanded(child: TextField(controller: _areaCtrl, decoration: InputDecoration(labelText: 'SqM', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                  ],
                ),
                SizedBox(height: 12),
                TextField(controller: _descCtrl, decoration: InputDecoration(labelText: 'Description', border: OutlineInputBorder()), maxLines: 3),
                SizedBox(height: 20),
                GestureDetector(
                  onTap: _pickImage,
                  child: Container(
                    height: 150,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.grey[200],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey),
                    ),
                    child: _imageBytes != null 
                      ? ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(Uint8List.fromList(_imageBytes!), fit: BoxFit.cover))
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [Icon(Icons.add_a_photo, size: 40, color: Colors.grey), Text("Upload Cover Image", style: TextStyle(color: Colors.grey))],
                        ),
                  ),
                ),
                SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _submit,
                    style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                    child: Text("Publish Listing", style: TextStyle(fontSize: 16)),
                  ),
                ),
              ],
            ),
          ),
    );
  }
}
'''
(LIB / "create_listing_screen.dart").write_text(CREATE_LISTING.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 4. Update Profile Screen
PROFILE_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'login_screen.dart';
import 'landlord_dashboard_screen.dart';

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
                  leading: Icon(Icons.home_work, color: Color(0xFF059669)),
                  title: Text("My Properties (Landlord)"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute(builder: (_) => LandlordDashboardScreen()));
                  },
                ),
                ListTile(
                  leading: Icon(Icons.verified_user, color: Color(0xFF059669)),
                  title: Text("Verification"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Verification coming soon to mobile!")));
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

print("""
==================================================
🎉 PHASE 29 COMPLETE: LANDLORD DASHBOARD & CREATE
==================================================

Go back to your terminal, quit ('q'), and restart the app.

Here is what is new:
1. Go to the **Profile** tab.
2. Click **My Properties (Landlord)**. (You can view this as the landlord account).
3. Click the **+ Floating Button** at the bottom right.
4. Fill in the property details, pick a location from the dropdown, and **tap the grey box to upload a cover image** from your computer.
5. Click **Publish Listing**. It will create the property, the listing, and upload the image directly to your Cloudinary account!
6. Once created, the property will appear in your Dashboard. Note that it will be in `DRAFT` status until you approve it in the Web Moderation Console.
""")