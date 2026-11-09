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
  int _unreadCount = 0;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _listings = ApiClient.getListings();
    _fetchNotifications();
  }

  Future<void> _fetchNotifications() async {
    try {
      final count = await ApiClient.getUnreadNotificationCount();
      if (mounted) setState(() => _unreadCount = count);
    } catch (e) {
      // User might not be logged in, ignore
    }
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
        title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 80),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),
        actions: [
          Stack(
            children: [
              IconButton(
                icon: Icon(Icons.notifications),
                onPressed: () async {
                  await Navigator.push(context, MaterialPageRoute(builder: (_) => NotificationsScreen()));
                  _fetchNotifications(); // Refresh badge when returning
                },
              ),
              if (_unreadCount > 0)
                Positioned(
                  right: 6,
                  top: 6,
                  child: Container(
                    padding: EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: BoxConstraints(minWidth: 18, minHeight: 18),
                    child: Text(
                      '$_unreadCount',
                      style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
        ],
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
