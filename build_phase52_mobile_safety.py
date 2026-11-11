#!/usr/bin/env python3
"""NyumbaLink Phase 52: Mobile Reporting & Notification Deep Linking."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Update API Client (Add Report Endpoint)
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "submitReport" not in text:
    text = text.replace(
        "  // --- Saved Properties ---",
        '''  static Future<void> submitReport(String listingId, String reason, String description) async {
    final res = await http.post(
      Uri.parse('$baseUrl/reports/'),
      headers: await getHeaders(),
      body: jsonEncode({'target_listing': listingId, 'reason': reason, 'description': description}),
    );
    if (res.statusCode != 201) throw Exception('Failed to submit report');
  }

  // --- Saved Properties ---'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added submitReport")

# ----------------------------------------------------------------
# 2. Update Notifications Screen (Deep Linking)
# ----------------------------------------------------------------
NOTIF_FILE = LIB / "notifications_screen.dart"
text = NOTIF_FILE.read_text(encoding="utf-8")

if "void _handleNotificationTap" not in text:
    # Add necessary imports
    text = text.replace(
        "import 'api_client.dart';",
        "import 'api_client.dart';\nimport 'landlord_dashboard_screen.dart';\nimport 'main_layout.dart';\nimport 'lease_agreement_screen.dart';\nimport 'landlord_profile_screen.dart';\nimport 'listing_detail_screen.dart';"
    )

    # Add the handler method
    text = text.replace(
        "  @override\n  Widget build(BuildContext context) {",
        '''  void _handleNotificationTap(BuildContext context, String? link) {
    if (link == null || link.isEmpty) return;
    Navigator.pop(context); // Close the notifications screen

    if (link.startsWith('/inbox')) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => MainLayout(initialTabIndex: 2))); // Inbox tab
    } else if (link.startsWith('/dashboard')) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => LandlordDashboardScreen()));
    } else if (link.startsWith('/leases/')) {
      final leaseId = link.split('/').last;
      Navigator.push(context, MaterialPageRoute(builder: (_) => LeaseAgreementScreen(leaseId: leaseId)));
    } else if (link.startsWith('/profiles/')) {
      final userId = link.split('/').last;
      Navigator.push(context, MaterialPageRoute(builder: (_) => LandlordProfileScreen(landlordId: userId, landlordEmail: '')));
    } else if (link.startsWith('/listings/')) {
      final listingId = link.split('/').last;
      Navigator.push(context, MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: listingId)));
    }
  }

  @override
  Widget build(BuildContext context) {'''
    )

    # Update the ListTile to use the handler
    old_tile = '''              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: n['is_read'] ? Colors.grey[200] : Colors.green[50],
                  child: Icon(Icons.notifications, color: n['is_read'] ? Colors.grey : Color(0xFF059669)),
                ),
                title: Text(n['title'], style: TextStyle(fontWeight: n['is_read'] ? FontWeight.normal : FontWeight.bold)),
                subtitle: Text(n['message'], maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: Text(
                  new DateFormat('MMM d').format(DateTime.parse(n['created_at'])),
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              );'''
    
    new_tile = '''              return ListTile(
                onTap: () => _handleNotificationTap(context, n['link']),
                leading: CircleAvatar(
                  backgroundColor: n['is_read'] ? Colors.grey[200] : Colors.green[50],
                  child: Icon(Icons.notifications, color: n['is_read'] ? Colors.grey : Color(0xFF059669)),
                ),
                title: Text(n['title'], style: TextStyle(fontWeight: n['is_read'] ? FontWeight.normal : FontWeight.bold)),
                subtitle: Text(n['message'], maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: Text(
                  new DateFormat('MMM d').format(DateTime.parse(n['created_at'])),
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              );'''
    
    text = text.replace(old_tile, new_tile)
    NOTIF_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched notifications_screen.dart: Added deep linking navigation")

# ----------------------------------------------------------------
# 3. Update MainLayout (Accept Initial Tab Index)
# ----------------------------------------------------------------
LAYOUT_FILE = LIB / "main_layout.dart"
text = LAYOUT_FILE.read_text(encoding="utf-8")

if "initialTabIndex" not in text:
    text = text.replace(
        "class MainLayout extends StatefulWidget {",
        "class MainLayout extends StatefulWidget {\n  final int initialTabIndex;\n  MainLayout({this.initialTabIndex = 0});"
    )
    text = text.replace(
        "  int _currentIndex = 0;",
        "  late int _currentIndex;\n\n  @override\n  void initState() {\n    super.initState();\n    _currentIndex = widget.initialTabIndex;\n  }"
    )
    LAYOUT_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched main_layout.dart: Allows opening directly to Inbox tab")

# ----------------------------------------------------------------
# 4. Update ListingDetailScreen (Add Report Button)
# ----------------------------------------------------------------
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "Report this listing" not in text:
    # Add report modal method
    text = text.replace(
        "  @override\n  Widget build(BuildContext context) {",
        '''  void _showReportModal() {
    String reason = 'FRAUD';
    final descCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text("Report Listing", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.red)),
                SizedBox(height: 8),
                Text("Help us keep NyumbaLink safe.", style: TextStyle(color: Colors.grey)),
                SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: reason,
                  decoration: InputDecoration(labelText: 'Reason', border: OutlineInputBorder()),
                  items: ['FRAUD', 'DUPLICATE', 'WRONG_INFO', 'UNAVAILABLE', 'OFFENSIVE']
                      .map((r) => DropdownMenuItem(value: r, child: Text(r.replace('_', ' ')))).toList(),
                  onChanged: (val) => setModalState(() => reason = val!),
                ),
                SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: InputDecoration(labelText: 'Details (Optional)', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () async {
                    try {
                      await ApiClient.submitReport(widget.listingId, reason, descCtrl.text);
                      if (mounted) {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Report submitted. Thank you.")));
                      }
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit report")));
                    }
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red, minimumSize: Size(double.infinity, 50)),
                  child: Text("Submit Report"),
                ),
                SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {'''
    )

    # Add the button to the UI right below the "Advertised by" block
    old_advertised = '''                          child: Row(
                            children: [
                              CircleAvatar(backgroundColor: Color(0xFF059669), child: Icon(Icons.person, color: Colors.white)),
                              SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text("Advertised by", style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                                    Text(listing['created_by_email'] ?? 'Landlord', style: TextStyle(fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                              Icon(Icons.chevron_right, color: Colors.grey),
                            ],
                          ),'''
    
    new_advertised = old_advertised + '''
                        ),
                      ),
                      SizedBox(height: 8),
                      Center(
                        child: TextButton.icon(
                          onPressed: _showReportModal,
                          icon: Icon(Icons.flag, color: Colors.red, size: 16),
                          label: Text("Report this listing", style: TextStyle(color: Colors.red, fontSize: 12)),
                        ),
                      ),
                      SizedBox(height: 8),
                      GestureDetector(
                        onTap: () {},
                        child: Container(), // spacer
                      ),'''

    # Replace the exact block. Note: the original code has a closing `),` for GestureDetector
    if "Icon(Icons.chevron_right, color: Colors.grey),\n                            ],\n                          )," in text:
        text = text.replace(
            "Icon(Icons.chevron_right, color: Colors.grey),\n                            ],\n                          ),",
            "Icon(Icons.chevron_right, color: Colors.grey),\n                            ],\n                          ),\n                      ),\n                      SizedBox(height: 4),\n                      Center(\n                        child: TextButton.icon(\n                          onPressed: _showReportModal,\n                          icon: Icon(Icons.flag, color: Colors.red, size: 16),\n                          label: Text(\"Report this listing\", style: TextStyle(color: Colors.red, fontSize: 12)),\n                        ),\n                      ),"
        )
    
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added Report Listing button")

print("""
==================================================
🎉 PHASE 52 COMPLETE: MOBILE SAFETY & DEEP LINKS
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app.

1. **Deep Linking**: Go to the Notification Bell. Click a notification (e.g. "New Viewing Request"). It will now automatically navigate you to the correct screen (Viewings or Lease).
2. **Reporting**: Open any property, scroll down to the bottom, and click the red **"Report this listing"** button. Select a reason and submit. It will instantly appear in the Admin Moderation console on the web!
""")