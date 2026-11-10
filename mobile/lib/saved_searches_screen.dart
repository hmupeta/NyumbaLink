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
