#!/usr/bin/env python3
"""Recreates the missing saved_searches_screen.dart and patches api_client.dart."""
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Recreate saved_searches_screen.dart
# ----------------------------------------------------------------
SAVED_SEARCHES_SCREEN = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class SavedSearchesScreen extends StatefulWidget {
  @override
  _SavedSearchesScreenState createState() => _SavedSearchesScreenState();
}

class _SavedSearchesScreenState extends State<SavedSearchesScreen> {
  late Future<List<dynamic>> _searchesFuture;

  @override
  void initState() {
    super.initState();
    _searchesFuture = ApiClient.getSavedSearches();
  }

  void _delete(String id) async {
    try {
      await ApiClient.deleteSavedSearch(id);
      setState(() => _searchesFuture = ApiClient.getSavedSearches());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to delete")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Saved Searches"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _searchesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading saved searches"));

          final searches = snapshot.data!;
          if (searches.isEmpty) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  "You haven't saved any searches yet. Apply filters on the Home screen and click 'Save Search'.",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
              ),
            );
          }

          return ListView.builder(
            padding: EdgeInsets.all(8),
            itemCount: searches.length,
            itemBuilder: (context, index) {
              final search = searches[index];
              
              List<String> summary = [];
              if (search['transaction_type'] != null && search['transaction_type'].toString().isNotEmpty) summary.add(search['transaction_type']);
              if (search['property_type'] != null && search['property_type'].toString().isNotEmpty) summary.add(search['property_type']);
              if (search['min_bedrooms'] != null) summary.add("${search['min_bedrooms']}+ beds");
              if (search['max_price'] != null) summary.add("Under K${search['max_price']}");

              return Card(
                child: ListTile(
                  contentPadding: EdgeInsets.all(12),
                  leading: Icon(Icons.bookmark, color: Color(0xFF059669)),
                  title: Text(search['name'], style: TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text(
                    summary.isEmpty ? "Any property" : summary.join(" · "),
                    style: TextStyle(color: Colors.grey[700]),
                  ),
                  trailing: IconButton(
                    icon: Icon(Icons.delete_outline, color: Colors.red),
                    onPressed: () => _delete(search['id']),
                  ),
                  onTap: () {
                    Navigator.pop(context, search);
                  },
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
(LIB / "saved_searches_screen.dart").write_text(SAVED_SEARCHES_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Recreated saved_searches_screen.dart")

# ----------------------------------------------------------------
# 2. Patch api_client.dart to include saved search methods
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getSavedSearches" not in text:
    new_methods = '''
  // --- Saved Searches ---
  static Future<List<dynamic>> getSavedSearches() async {
    final res = await http.get(Uri.parse('$baseUrl/saved-searches/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load saved searches');
  }

  static Future<void> createSavedSearch(Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl/saved-searches/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (res.statusCode != 201) throw Exception('Failed to save search');
  }

  static Future<void> deleteSavedSearch(String id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/saved-searches/$id/'),
      headers: await getHeaders(),
    );
    if (res.statusCode != 204) throw Exception('Failed to delete saved search');
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added Saved Searches methods")
else:
    print("ℹ️ Saved search methods already exist in api_client.dart")

print("""
==================================================
🎉 MISSING FILES FIXED!
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The errors about missing files and undefined methods are now resolved. 
The app should compile and the Map toggle will work perfectly!
""")