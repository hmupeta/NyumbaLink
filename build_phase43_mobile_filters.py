#!/usr/bin/env python3
"""NyumbaLink Phase 43: Mobile Advanced Search & Filters."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Flutter: Update API Client to accept filters
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

old_get_listings = '''  static Future<List<dynamic>> getListings({String? query}) async {
    String url = '$baseUrl/listings/';
    if (query != null && query.isNotEmpty) url += '?search=$query';
    final res = await http.get(Uri.parse(url), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load listings');
  }'''

new_get_listings = '''  static Future<List<dynamic>> getListings({
    String? query, 
    String? transactionType, 
    String? propertyType, 
    int? minBedrooms, 
    double? maxPrice
  }) async {
    final params = <String, String>{};
    if (query != null && query.isNotEmpty) params['search'] = query;
    if (transactionType != null && transactionType.isNotEmpty) params['transaction_type'] = transactionType;
    if (propertyType != null && propertyType.isNotEmpty) params['property_type'] = propertyType;
    if (minBedrooms != null) params['min_bedrooms'] = minBedrooms.toString();
    if (maxPrice != null) params['max_price'] = maxPrice.toString();

    final uri = Uri.parse('$baseUrl/listings/').replace(queryParameters: params);
    final res = await http.get(uri, headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load listings');
  }'''

if old_get_listings in text:
    text = text.replace(old_get_listings, new_get_listings)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added filter parameters to getListings")
else:
    print("⚠️ Could not find exact getListings method.")

# ----------------------------------------------------------------
# 2. Flutter: Update Home Screen with Filter UI
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"

NEW_HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'listing_detail_screen.dart';
import 'notifications_screen.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _listings;
  final _searchController = TextEditingController();
  int _unreadCount = 0;

  // Filter State
  String? _transactionType;
  String? _propertyType;
  int? _minBedrooms;
  double? _maxPrice;
  
  final _priceController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchListings();
    _fetchNotifications();
  }

  void _fetchListings() {
    setState(() {
      _listings = ApiClient.getListings(
        query: _searchController.text,
        transactionType: _transactionType,
        propertyType: _propertyType,
        minBedrooms: _minBedrooms,
        maxPrice: _maxPrice,
      );
    });
  }

  Future<void> _fetchNotifications() async {
    try {
      final count = await ApiClient.getUnreadNotificationCount();
      if (mounted) setState(() => _unreadCount = count);
    } catch (e) {}
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  void _showFilterSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                left: 16, right: 16, top: 24
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Filters", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                      TextButton(
                        onPressed: () {
                          setModalState(() {
                            _transactionType = null;
                            _propertyType = null;
                            _minBedrooms = null;
                            _maxPrice = null;
                            _priceController.clear();
                          });
                        },
                        child: Text("Clear All", style: TextStyle(color: Colors.red)),
                      )
                    ],
                  ),
                  SizedBox(height: 16),
                  
                  Text("Transaction Type", style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  Row(
                    children: [
                      _buildChoiceChip("Rent", _transactionType == 'RENT', () => setModalState(() => _transactionType = 'RENT')),
                      SizedBox(width: 8),
                      _buildChoiceChip("Buy", _transactionType == 'SALE', () => setModalState(() => _transactionType = 'SALE')),
                    ],
                  ),
                  SizedBox(height: 16),

                  Text("Property Type", style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: _propertyType,
                    decoration: InputDecoration(labelText: 'Select Property Type', border: OutlineInputBorder()),
                    items: ['HOUSE', 'APARTMENT', 'TOWNHOUSE', 'LAND']
                        .map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                    onChanged: (val) => setModalState(() => _propertyType = val),
                  ),
                  SizedBox(height: 16),

                  Text("Min Bedrooms", style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  Row(
                    children: [1, 2, 3, 4].map((num) {
                      return Padding(
                        padding: const EdgeInsets.only(right: 8.0),
                        child: _buildChoiceChip("$num", _minBedrooms == num, () => setModalState(() => _minBedrooms = num)),
                      );
                    }).toList(),
                  ),
                  SizedBox(height: 16),

                  Text("Max Price (ZMW)", style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  TextField(
                    controller: _priceController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(hintText: "e.g. 10000", border: OutlineInputBorder()),
                    onChanged: (val) {
                      _maxPrice = double.tryParse(val);
                    },
                  ),
                  SizedBox(height: 24),

                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _fetchListings();
                      },
                      style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                      child: Text("Apply Filters"),
                    ),
                  ),
                  SizedBox(height: 16),
                ],
              ),
            );
          }
        );
      }
    );
  }

  Widget _buildChoiceChip(String label, bool isSelected, VoidCallback onTap) {
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => onTap(),
      selectedColor: Color(0xFF059669).withOpacity(0.2),
      labelStyle: TextStyle(color: isSelected ? Color(0xFF059669) : Colors.black),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 80),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),
        backgroundColor: Color(0xFF059669),
        automaticallyImplyLeading: false,
        actions: [
          Stack(
            children: [
              IconButton(
                icon: Icon(Icons.notifications),
                onPressed: () async {
                  await Navigator.push(context, MaterialPageRoute(builder: (_) => NotificationsScreen()));
                  _fetchNotifications();
                },
              ),
              if (_unreadCount > 0)
                Positioned(
                  right: 6,
                  top: 6,
                  child: Container(
                    padding: EdgeInsets.all(4),
                    decoration: BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                    constraints: BoxConstraints(minWidth: 18, minHeight: 18),
                    child: Text('$_unreadCount', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                  ),
                ),
            ],
          ),
        ],
        bottom: PreferredSize(
          preferredSize: Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    onSubmitted: (_) => _fetchListings(),
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
                SizedBox(width: 8),
                Container(
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(30)),
                  child: IconButton(
                    icon: Icon(Icons.tune, color: Color(0xFF059669)),
                    onPressed: _showFilterSheet,
                    tooltip: "Filters",
                  ),
                ),
              ],
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
          if (listings.isEmpty) return Center(child: Text("No properties found. Try clearing filters."));

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
HOME_FILE.write_text(NEW_HOME_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Patched home_screen.dart: Added Advanced Filter UI and logic")

print("""
==================================================
🎉 PHASE 43 COMPLETE: MOBILE FILTERS
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. On the Home Screen, next to the search bar, you will see a **Filter icon** (tune icon).
2. Tap it to open the bottom sheet.
3. Select "Rent", "Apartment", and 2 bedrooms. Enter a max price like 8000.
4. Click Apply Filters. The list will instantly filter to match your criteria!
""")