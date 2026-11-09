#!/usr/bin/env python3
"""NyumbaLink Phase 33: Mobile Notifications and Viewing Requests."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Update API Client
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getViewingRequests" not in text:
    new_methods = '''
  // --- Notifications ---
  static Future<int> getUnreadNotificationCount() async {
    final res = await http.get(Uri.parse('$baseUrl/notifications/unread_count/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['count'];
    return 0;
  }

  static Future<List<dynamic>> getNotifications() async {
    final res = await http.get(Uri.parse('$baseUrl/notifications/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load notifications');
  }

  static Future<void> markAllNotificationsRead() async {
    await http.post(Uri.parse('$baseUrl/notifications/mark_all_read/'), headers: await getHeaders());
  }

  // --- Viewing Requests ---
  static Future<void> requestViewing(String listingId, String dateIso) async {
    final res = await http.post(
      Uri.parse('$baseUrl/viewings/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing': listingId, 'requested_date': dateIso, 'note': 'Requested via mobile app'}),
    );
    if (res.statusCode != 201) throw Exception('Failed to request viewing');
  }

  static Future<List<dynamic>> getViewingRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/viewings/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load viewing requests');
  }

  static Future<void> updateViewingStatus(String viewingId, String status) async {
    final res = await http.post(
      Uri.parse('$baseUrl/viewings/$viewingId/update_status/'),
      headers: await getHeaders(),
      body: jsonEncode({'status': status}),
    );
    if (res.statusCode != 200) throw Exception('Failed to update status');
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added notification and viewing methods")

# ---------------------------------------------------------------- 2. Create Notifications Screen
NOTIFICATIONS_SCREEN = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class NotificationsScreen extends StatefulWidget {
  @override
  _NotificationsScreenState createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<dynamic>> _notificationsFuture;

  @override
  void initState() {
    super.initState();
    _notificationsFuture = ApiClient.getNotifications();
    // Mark all as read when we open the screen
    ApiClient.markAllNotificationsRead();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Notifications"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _notificationsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading notifications."));

          final notifs = snapshot.data!;
          if (notifs.isEmpty) return Center(child: Text("No notifications yet."));

          return ListView.builder(
            itemCount: notifs.length,
            itemBuilder: (context, index) {
              final n = notifs[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: n['is_read'] ? Colors.grey[200] : Colors.emerald[50],
                  child: Icon(Icons.notifications, color: n['is_read'] ? Colors.grey : Color(0xFF059669)),
                ),
                title: Text(n['title'], style: TextStyle(fontWeight: n['is_read'] ? FontWeight.normal : FontWeight.bold)),
                subtitle: Text(n['message'], maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: Text(
                  new DateFormat('MMM d').format(DateTime.parse(n['created_at'])),
                  style: TextStyle(fontSize: 12, color: Colors.grey),
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
# Add DateFormat import
NOTIFICATIONS_SCREEN = "import 'package:intl/intl.dart';\n" + NOTIFICATIONS_SCREEN
(LIB / "notifications_screen.dart").write_text(NOTIFICATIONS_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created notifications_screen.dart")

# ---------------------------------------------------------------- 3. Create Viewing Requests Screen
VIEWINGS_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'api_client.dart';

class ViewingRequestsScreen extends StatefulWidget {
  @override
  _ViewingRequestsScreenState createState() => _ViewingRequestsScreenState();
}

class _ViewingRequestsScreenState extends State<ViewingRequestsScreen> {
  late Future<List<dynamic>> _viewingsFuture;

  @override
  void initState() {
    super.initState();
    _loadViewings();
  }

  void _loadViewings() {
    setState(() {
      _viewingsFuture = ApiClient.getViewingRequests();
    });
  }

  void _updateStatus(String id, String status) async {
    try {
      await ApiClient.updateViewingStatus(id, status);
      _loadViewings(); // Refresh list
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to update status")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Viewing Requests"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _viewingsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading requests."));

          final viewings = snapshot.data!;
          if (viewings.isEmpty) return Center(child: Text("No viewing requests yet."));

          return ListView.builder(
            padding: EdgeInsets.all(8),
            itemCount: viewings.length,
            itemBuilder: (context, index) {
              final v = viewings[index];
              final status = v['status'];
              final date = DateTime.parse(v['requested_date']);
              
              return Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(v['listing_title'], style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      SizedBox(height: 4),
                      Text("Seeker: ${v['seeker_email']}", style: TextStyle(color: Colors.grey)),
                      Text("Requested for: ${DateFormat('MMM d, yyyy - h:mm a').format(date)}"),
                      SizedBox(height: 12),
                      if (status == 'PENDING') ...[
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton(
                                onPressed: () => _updateStatus(v['id'], 'APPROVED'),
                                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                                child: Text("Approve"),
                              ),
                            ),
                            SizedBox(width: 8),
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () => _updateStatus(v['id'], 'REJECTED'),
                                style: OutlinedButton.styleFrom(foregroundColor: Colors.red, side: BorderSide(color: Colors.red)),
                                child: Text("Reject"),
                              ),
                            ),
                          ],
                        )
                      ] else ...[
                        Container(
                          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: status == 'APPROVED' ? Colors.green[100] : Colors.red[100],
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            status,
                            style: TextStyle(
                              color: status == 'APPROVED' ? Colors.green[800] : Colors.red[800],
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        )
                      ]
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
(LIB / "viewing_requests_screen.dart").write_text(VIEWINGS_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created viewing_requests_screen.dart")

# ---------------------------------------------------------------- 4. Add Bell to Home Screen AppBar
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

if "NotificationsScreen" not in text:
    text = text.replace(
        "import 'listing_detail_screen.dart';",
        "import 'listing_detail_screen.dart';\nimport 'notifications_screen.dart';"
    )
    
    old_appbar = '''        title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 80),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),'''
    
    new_appbar = '''        title: Row(
          children: [
            Image.asset("assets/images/logo.png", height: 80),
            SizedBox(width: 8),
            Text("NyumbaLink"),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.notifications),
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => NotificationsScreen()));
            },
          ),
        ],'''
    
    text = text.replace(old_appbar, new_appbar)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Added notification bell")

# ---------------------------------------------------------------- 5. Add Viewing Requests button to Landlord Dashboard
DASHBOARD_FILE = LIB / "landlord_dashboard_screen.dart"
text = DASHBOARD_FILE.read_text(encoding="utf-8")

if "ViewingRequestsScreen" not in text:
    text = text.replace(
        "import 'manage_listing_screen.dart';",
        "import 'manage_listing_screen.dart';\nimport 'viewing_requests_screen.dart';"
    )
    
    old_appbar = '''      appBar: AppBar(title: Text("My Properties"), backgroundColor: Color(0xFF059669)),'''
    new_appbar = '''      appBar: AppBar(
        title: Text("My Properties"), 
        backgroundColor: Color(0xFF059669),
        actions: [
          IconButton(
            icon: Icon(Icons.calendar_today),
            tooltip: "Viewing Requests",
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ViewingRequestsScreen())),
          )
        ],
      ),'''
    
    text = text.replace(old_appbar, new_appbar)
    DASHBOARD_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched landlord_dashboard_screen.dart: Added Viewing Requests button")

# ---------------------------------------------------------------- 6. Add Request Viewing to Detail Screen
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "requestViewing" not in text:
    # Add a button next to "Message Landlord"
    old_buttons = '''                          : ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                            ),
                      ),'''
    
    new_buttons = '''                          : Column(
                              children: [
                                ElevatedButton.icon(
                                  onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                                  icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                                  label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Color(0xFF059669), 
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    minimumSize: Size(double.infinity, 50),
                                  ),
                                ),
                                SizedBox(height: 12),
                                OutlinedButton.icon(
                                  onPressed: () async {
                                    final date = await showDatePicker(
                                      context: context,
                                      initialDate: DateTime.now().add(Duration(days: 1)),
                                      firstDate: DateTime.now(),
                                      lastDate: DateTime.now().add(Duration(days: 30)),
                                    );
                                    if (date != null) {
                                      try {
                                        await ApiClient.requestViewing(listing['id'], date.toIso8601String());
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Viewing requested for ${date.toString().split(' ')[0]}")));
                                      } catch (e) {
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to request viewing")));
                                      }
                                    }
                                  },
                                  icon: Icon(Icons.calendar_today, color: Color(0xFF059669)),
                                  label: Text("Request Viewing", style: TextStyle(color: Color(0xFF059669))),
                                  style: OutlinedButton.styleFrom(
                                    side: BorderSide(color: Color(0xFF059669)),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    minimumSize: Size(double.infinity, 50),
                                  ),
                                ),
                              ]
                            ),
                      ),'''
    
    text = text.replace(old_buttons, new_buttons)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added Request Viewing button")

print("""
==================================================
🎉 PHASE 33 COMPLETE: MOBILE VIEWINGS & NOTIFICATIONS
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. **Notification Bell**: You will see a Bell icon in the top right of the Home Screen. Tapping it opens your notifications.
2. **Request Viewing**: On a property detail page, below the "Message Landlord" button, there is a new "Request Viewing" button that lets you pick a date.
3. **Landlord Dashboard**: Go to Profile -> My Properties. You will see a Calendar icon in the top right. Tap it to see all incoming viewing requests and approve or reject them!
""")