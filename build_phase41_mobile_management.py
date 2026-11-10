#!/usr/bin/env python3
"""NyumbaLink Phase 41: Mobile Tenant & Maintenance Management."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getLeases" not in text:
    new_methods = '''
  // --- Management (Tenants & Leases) ---
  static Future<List<dynamic>> getLeases() async {
    final res = await http.get(Uri.parse('$baseUrl/leases/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load leases');
  }

  static Future<void> markRentPaid(String leaseId, String recordId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/leases/$leaseId/rent-records/$recordId/mark_paid/'),
      headers: await getHeaders(),
    );
    if (res.statusCode != 200) throw Exception('Failed to mark rent paid');
  }

  // --- Maintenance ---
  static Future<List<dynamic>> getMaintenanceRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/maintenance/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load maintenance requests');
  }

  static Future<void> updateMaintenanceStatus(String id, String status) async {
    final res = await http.post(
      Uri.parse('$baseUrl/maintenance/$id/update_status/'),
      headers: await getHeaders(),
      body: jsonEncode({'status': status}),
    );
    if (res.statusCode != 200) throw Exception('Failed to update maintenance status');
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added management methods")

# ----------------------------------------------------------------
# 2. Flutter: Create Tenants Tab
# ----------------------------------------------------------------
TENANTS_TAB = '''
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'api_client.dart';

class TenantsTab extends StatefulWidget {
  @override
  _TenantsTabState createState() => _TenantsTabState();
}

class _TenantsTabState extends State<TenantsTab> {
  late Future<List<dynamic>> _leasesFuture;

  @override
  void initState() {
    super.initState();
    _leasesFuture = ApiClient.getLeases();
  }

  void _markPaid(String leaseId, String recordId) async {
    try {
      await ApiClient.markRentPaid(leaseId, recordId);
      setState(() => _leasesFuture = ApiClient.getLeases());
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Rent marked as paid!")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to update rent")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<dynamic>>(
      future: _leasesFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return Center(child: Text("Error loading tenants"));

        final leases = snapshot.data!;
        if (leases.isEmpty) return Center(child: Text("No active tenants."));

        return ListView.builder(
          padding: EdgeInsets.all(8),
          itemCount: leases.length,
          itemBuilder: (context, index) {
            final lease = leases[index];
            final records = lease['rent_records'] as List<dynamic>? ?? [];
            final pendingRent = records.where((r) => r['status'] == 'PENDING').toList();

            return Card(
              child: ExpansionTile(
                title: Text(lease['tenant_name'], style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(lease['property_name']),
                    SizedBox(height: 4),
                    Text(
                      pendingRent.isEmpty ? "Rent Up to Date" : "${pendingRent.length} Payment(s) Pending",
                      style: TextStyle(color: pendingRent.isEmpty ? Colors.green : Colors.red, fontWeight: FontWeight.bold, fontSize: 12),
                    )
                  ],
                ),
                children: records.map((record) {
                  final isPaid = record['status'] == 'PAID';
                  return ListTile(
                    leading: Icon(isPaid ? Icons.check_circle : Icons.pending_actions, color: isPaid ? Colors.green : Colors.orange),
                    title: Text("Due: ${DateFormat('MMM yyyy').format(DateTime.parse(record['due_date']))}"),
                    subtitle: Text("K ${record['amount']}"),
                    trailing: isPaid 
                      ? Text("Paid", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold))
                      : ElevatedButton(
                          onPressed: () => _markPaid(lease['id'], record['id']),
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
                          child: Text("Mark Paid"),
                        ),
                  );
                }).toList(),
              ),
            );
          },
        );
      },
    );
  }
}
'''
(LIB / "tenants_tab.dart").write_text(TENANTS_TAB.strip() + "\n", encoding="utf-8")
print("✅ Created tenants_tab.dart")

# ----------------------------------------------------------------
# 3. Flutter: Create Maintenance Tab
# ----------------------------------------------------------------
MAINTENANCE_TAB = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class MaintenanceTab extends StatefulWidget {
  @override
  _MaintenanceTabState createState() => _MaintenanceTabState();
}

class _MaintenanceTabState extends State<MaintenanceTab> {
  late Future<List<dynamic>> _requestsFuture;

  @override
  void initState() {
    super.initState();
    _requestsFuture = ApiClient.getMaintenanceRequests();
  }

  void _updateStatus(String id, String status) async {
    try {
      await ApiClient.updateMaintenanceStatus(id, status);
      setState(() => _requestsFuture = ApiClient.getMaintenanceRequests());
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to update status")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<dynamic>>(
      future: _requestsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return Center(child: Text("Error loading maintenance"));

        final requests = snapshot.data!;
        if (requests.isEmpty) return Center(child: Text("No maintenance issues logged."));

        return ListView.builder(
          padding: EdgeInsets.all(8),
          itemCount: requests.length,
          itemBuilder: (context, index) {
            final req = requests[index];
            final status = req['status'];
            final priority = req['priority'];

            Color priorityColor = priority == 'HIGH' ? Colors.red : priority == 'MEDIUM' ? Colors.orange : Colors.grey;

            return Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(color: priorityColor.withOpacity(0.1), borderRadius: BorderRadius.circular(4)),
                          child: Text(priority, style: TextStyle(color: priorityColor, fontSize: 10, fontWeight: FontWeight.bold)),
                        ),
                        Text(status, style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey[700], fontSize: 12)),
                      ],
                    ),
                    SizedBox(height: 12),
                    Text(req['title'], style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    SizedBox(height: 4),
                    Text(req['description'], maxLines: 2, overflow: TextOverflow.ellipsis),
                    SizedBox(height: 16),
                    
                    // Action Buttons
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        if (status == 'OPEN')
                          ElevatedButton(
                            onPressed: () => _updateStatus(req['id'], 'IN_PROGRESS'),
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
                            child: Text("Start Work"),
                          )
                        else if (status == 'IN_PROGRESS')
                          ElevatedButton(
                            onPressed: () => _updateStatus(req['id'], 'RESOLVED'),
                            style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                            child: Text("Mark Resolved"),
                          )
                        else
                          Text("Resolved ✓", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                      ],
                    )
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}
'''
(LIB / "maintenance_tab.dart").write_text(MAINTENANCE_TAB.strip() + "\n", encoding="utf-8")
print("✅ Created maintenance_tab.dart")

# ----------------------------------------------------------------
# 4. Flutter: Update Landlord Dashboard (Add Tabs)
# ----------------------------------------------------------------
DASHBOARD_FILE = LIB / "landlord_dashboard_screen.dart"

NEW_DASHBOARD = '''
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
'''
DASHBOARD_FILE.write_text(NEW_DASHBOARD.strip() + "\n", encoding="utf-8")
print("✅ Patched landlord_dashboard_screen.dart: Converted to Tabbed Dashboard")

print("""
==================================================
🎉 PHASE 41 COMPLETE: MOBILE TENANT & MAINTENANCE
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. Go to Profile -> My Properties (Landlord).
2. Notice the new tabs at the top: **Properties**, **Tenants**, and **Maintenance**.
3. Click **Tenants** to see active leases and mark rent as paid.
4. Click **Maintenance** to see reported issues. Try moving an issue from "Open" -> "In Progress" -> "Resolved".
""")