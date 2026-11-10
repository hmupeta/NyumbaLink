import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';
import 'package:latlong2/latlong.dart';
import 'listing_detail_screen.dart';

class MapView extends StatelessWidget {
  final List<dynamic> listings;

  MapView({required this.listings});

  @override
  Widget build(BuildContext context) {
    // Default to Lusaka center
    final center = LatLng(-15.416, 28.283);

    // Filter listings that have valid coordinates
    final validListings = listings.where((l) {
      final coords = l['property_summary'];
      return coords != null && coords['latitude'] != null && coords['longitude'] != null;
    }).toList();

    return Stack(
      children: [
        FlutterMap(
          options: MapOptions(
            initialCenter: center,
            initialZoom: 12.0,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.nyumbalink.mobile',
              tileProvider: CancellableNetworkTileProvider(),
            ),
            MarkerLayer(
              markers: validListings.map((l) {
                final lat = double.parse(l['property_summary']['latitude'].toString());
                final lng = double.parse(l['property_summary']['longitude'].toString());
                final price = l['price'];

                return Marker(
                  point: LatLng(lat, lng),
                  width: 80,
                  height: 40,
                  child: GestureDetector(
                    onTap: () {
                      Navigator.push(context, MaterialPageRoute(
                        builder: (_) => ListingDetailScreen(listingId: l['id'])
                      ));
                    },
                    child: Container(
                      decoration: BoxDecoration(
                        color: Color(0xFF059669),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: Colors.white, width: 2),
                        boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        "K$price",
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
        if (validListings.isEmpty)
          Positioned(
            bottom: 24, left: 24, right: 24,
            child: Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8), boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8)]),
              child: Text("No properties with location data found. Try clearing filters.", textAlign: TextAlign.center),
            ),
          ),
      ],
    );
  }
}
