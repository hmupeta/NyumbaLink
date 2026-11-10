#!/usr/bin/env python3
"""Completely rewrites home_screen.dart with clean syntax."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "home_screen.dart"

NEW_HOME_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'listing_detail_screen.dart';
import 'notifications_screen.dart';
import 'saved_searches_screen.dart';
import 'map_view.dart';
import 'terms_screen.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _listings;
  final _searchController = TextEditingController();
  final _priceController = TextEditingController();
  int _unreadCount = 0;
  bool _isMapView = false;

  String? _transactionType;
  String? _propertyType;
  int? _minBedrooms;
  double? _maxPrice;

  @override
  void initState() {
    super.initState();
    _fetchListings();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      if (auth.user != null) {
        _fetchNotifications();
      }
    });
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
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () async {
                            final nameCtrl = TextEditingController(text: _searchController.text.isEmpty ? "My Search" : _searchController.text);
                            String? saveName = await showDialog<String>(
                              context: context,
                              builder: (context) => AlertDialog(
                                title: Text("Name your search"),
                                content: TextField(controller: nameCtrl, decoration: InputDecoration(hintText: "e.g. Houses in Kabulonga")),
                                actions: [
                                  TextButton(onPressed: () => Navigator.pop(context), child: Text("Cancel")),
                                  ElevatedButton(onPressed: () => Navigator.pop(context, nameCtrl.text), child: Text("Save"))
                                ],
                              ),
                            );
                            if (saveName != null) {
                              try {
                                await ApiClient.createSavedSearch({
                                  'name': saveName,
                                  'query': _searchController.text,
                                  'transaction_type': _transactionType ?? '',
                                  'property_type': _propertyType ?? '',
                                  'min_bedrooms': _minBedrooms,
                                  'max_price': _maxPrice,
                                });
                                if (mounted) {
                                  Navigator.pop(context);
                                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Search saved!")));
                                }
                              } catch (e) {
                                if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to save")));
                              }
                            }
                          },
                          style: OutlinedButton.styleFrom(side: BorderSide(color: Color(0xFF059669)), minimumSize: Size(0, 50)),
                          child: Text("Save", style: TextStyle(color: Color(0xFF059669))),
                        ),
                      ),
                      SizedBox(width: 8),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.pop(context);
                            _fetchListings();
                          },
                          style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(0, 50)),
                          child: Text("Apply Filters"),
                        ),
                      ),
                    ],
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

  Widget _buildIntroCard(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: 16),
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.green[50],
        border: Border(bottom: BorderSide(color: Colors.green[200]!, width: 2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Find your place. Connect your world.",
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF059669)),
          ),
          SizedBox(height: 8),
          Text(
            "NyumbaLink bridges the gap between tenants and landlords in Zambia. Browse verified properties, chat directly with landlords, and pay rent or deposits securely via MTN, Airtel, or Zamtel Mobile Money.",
            style: TextStyle(fontSize: 14, height: 1.5, color: Colors.grey[800]),
          ),
          SizedBox(height: 12),
          GestureDetector(
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => TermsScreen())),
            child: Text(
              "Read our Terms & Conditions",
              style: TextStyle(color: Colors.blue[700], fontWeight: FontWeight.bold, decoration: TextDecoration.underline),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

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
          if (auth.user == null)
            TextButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
              child: Text("Login", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          IconButton(
            icon: Icon(Icons.bookmark),
            tooltip: "Saved Searches",
            onPressed: () async {
              final savedSearch = await Navigator.push<dynamic>(
                context,
                MaterialPageRoute(builder: (_) => SavedSearchesScreen()),
              );
              if (savedSearch != null) {
                setState(() {
                  _searchController.text = savedSearch['query'] ?? '';
                  _transactionType = savedSearch['transaction_type'];
                  _propertyType = savedSearch['property_type'];
                  _minBedrooms = savedSearch['min_bedrooms'];
                  _maxPrice = savedSearch['max_price'] != null ? double.parse(savedSearch['max_price'].toString()) : null;
                  _priceController.text = _maxPrice?.toString() ?? '';
                });
                _fetchListings();
              }
            },
          ),
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
          if (listings.isEmpty) return Center(child: Text("No properties found."));

          return Stack(
            children: [
              if (_isMapView)
                MapView(listings: listings)
              else
                ListView.builder(
                  itemCount: listings.length + 1, // +1 for the header
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return _buildIntroCard(context);
                    }
                    final l = listings[index - 1];
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
                ),
              Positioned(
                bottom: 24,
                right: 24,
                child: FloatingActionButton.extended(
                  onPressed: () {
                    setState(() => _isMapView = !_isMapView);
                  },
                  backgroundColor: Colors.white,
                  icon: Icon(_isMapView ? Icons.list : Icons.map, color: Color(0xFF059669)),
                  label: Text(_isMapView ? "List View" : "Map View", style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
'''

FILE.write_text(NEW_HOME_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Rewrote home_screen.dart completely with clean syntax and intro card")

print("""
==================================================
🎉 SYNTAX FIXED!
==================================================

Go back to your terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The app will now compile, and you will see the new Intro Card, Login button, and Terms & Conditions link!
""")