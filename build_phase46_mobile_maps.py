#!/usr/bin/env python3
"""NyumbaLink Phase 46: Interactive Maps for Mobile."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Install flutter_map
# ----------------------------------------------------------------
print("📦 Installing flutter_map...")
PUBSPEC = MOBILE / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")

if "flutter_map" not in text:
    text = text.replace(
        "  intl: ^0.18.1",
        "  intl: ^0.18.1\n  flutter_map: ^6.1.0\n  latlong2: ^0.9.0"
    )
    PUBSPEC.write_text(text, encoding="utf-8")
    subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)
    print("✅ Added flutter_map and latlong2 dependencies")

# ----------------------------------------------------------------
# 2. Create MapView Widget
# ----------------------------------------------------------------
MAP_VIEW = '''
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
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
'''
(LIB / "map_view.dart").write_text(MAP_VIEW.strip() + "\n", encoding="utf-8")
print("✅ Created map_view.dart")

# ----------------------------------------------------------------
# 3. Update Home Screen (Add Toggle)
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

if "MapView" not in text:
    text = text.replace(
        "import 'saved_searches_screen.dart';",
        "import 'saved_searches_screen.dart';\nimport 'map_view.dart';"
    )
    
    # Add state for view mode
    text = text.replace(
        "  int _unreadCount = 0;",
        "  int _unreadCount = 0;\n  bool _isMapView = false;"
    )

    # Add toggle buttons above the list
    old_body = '''      body: FutureBuilder<List<dynamic>>(
        future: _listings,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings"));
          
          final listings = snapshot.data!;
          if (listings.isEmpty) return Center(child: Text("No properties found. Try clearing filters."));

          return ListView.builder('''

    new_body = '''      body: FutureBuilder<List<dynamic>>(
        future: _listings,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading listings"));
          
          final listings = snapshot.data!;
          if (listings.isEmpty) return Center(child: Text("No properties found. Try clearing filters."));

          if (_isMapView) {
            return MapView(listings: listings);
          }

          return Stack(
            children: [
              ListView.builder('''
    
    text = text.replace(old_body, new_body)

    # Close the stack at the end of the ListView
    old_end = '''              );
            },
          );
        },
      ),
    );
  }
}'''
    new_end = '''              );
            },
          ),
          
          // Floating Map/List Toggle
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
      ),
    );
  }
}'''
    
    text = text.replace(old_end, new_end)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Added Map/List toggle")

print("""
==================================================
🎉 PHASE 46 COMPLETE: MOBILE MAPS
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. On the Home screen, you will see a floating button at the bottom right that says **Map View**.
2. Tap it. The app will switch to a full-screen OpenStreetMap showing green price pins for every property.
3. Tap a pin to go straight to that property's details.
4. Tap the button again (now saying **List View**) to return to the standard grid.
""")