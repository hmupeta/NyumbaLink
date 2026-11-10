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
          if (snapshot.hasError) return Center(child: Padding(padding: EdgeInsets.all(24), child: Text("Please log in to view your saved properties.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey))));
          
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
