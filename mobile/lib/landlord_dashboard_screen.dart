import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';
import 'create_listing_screen.dart';
import 'manage_listing_screen.dart';
import 'viewing_requests_screen.dart';
import 'tenants_tab.dart';
import 'maintenance_tab.dart';

class LandlordDashboardScreen extends StatefulWidget {
  @override
  _LandlordDashboardScreenState createState() => _LandlordDashboardScreenState();
}

class _LandlordDashboardScreenState extends State<LandlordDashboardScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text("Landlord Dashboard"), 
          backgroundColor: Color(0xFF059669),
          actions: [
            IconButton(
              icon: Icon(Icons.calendar_today),
              tooltip: "Viewing Requests",
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ViewingRequestsScreen())),
            )
          ],
          bottom: TabBar(
            indicatorColor: Colors.white,
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            tabs: [
              Tab(text: "Properties"),
              Tab(text: "Tenants"),
              Tab(text: "Maintenance"),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _PropertiesTab(),
            TenantsTab(),
            MaintenanceTab(),
          ],
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => CreateListingScreen()));
          },
          backgroundColor: Color(0xFF059669),
          child: Icon(Icons.add, color: Colors.white),
        ),
      ),
    );
  }
}

class _PropertiesTab extends StatefulWidget {
  @override
  _PropertiesTabState createState() => _PropertiesTabState();
}

class _PropertiesTabState extends State<_PropertiesTab> {
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
    return FutureBuilder<List<dynamic>>(
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
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => ManageListingScreen(
                      listingId: l['id'],
                      onUpdate: _loadListings,
                    )),
                  );
                },
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
    );
  }
}
