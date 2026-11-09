#!/usr/bin/env python3
"""NyumbaLink Phase 34: Smart Viewing Buttons & Notification Badges."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Update ListingDetailScreen
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

# 1a. Add state variable for viewing status
if "String? _viewingStatus" not in text:
    text = text.replace(
        "  bool _isSaved = false;\n  bool _isSaving = false;",
        "  bool _isSaved = false;\n  bool _isSaving = false;\n  String? _viewingStatus; // Tracks 'PENDING', 'APPROVED', 'REJECTED'\n  bool _checkingViewing = true;"
    )

# 1b. Fetch viewing status on load
old_init = '''  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId);
  }'''
new_init = '''  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId);
    _checkViewingStatus();
  }

  Future<void> _checkViewingStatus() async {
    try {
      final requests = await ApiClient.getViewingRequests();
      final req = requests.firstWhere(
        (r) => r['listing'].toString() == widget.listingId,
        orElse: () => null,
      );
      if (mounted) {
        setState(() {
          _viewingStatus = req != null ? req['status'] : null;
          _checkingViewing = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _checkingViewing = false);
    }
  }'''
text = text.replace(old_init, new_init)

# 1c. Replace the OutlinedButton with a dynamic widget
old_button = '''                            OutlinedButton.icon(
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
                            ),'''

new_button = '''                            _checkingViewing 
                              ? SizedBox(height: 50, child: Center(child: CircularProgressIndicator()))
                              : _viewingStatus == 'APPROVED'
                                ? Container(
                                    height: 50,
                                    decoration: BoxDecoration(
                                      color: Colors.green[50],
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: Colors.green),
                                    ),
                                    child: Center(child: Text("✓ Viewing Approved", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                                  )
                                : _viewingStatus == 'PENDING'
                                  ? Container(
                                      height: 50,
                                      decoration: BoxDecoration(
                                        color: Colors.orange[50],
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: Colors.orange),
                                      ),
                                      child: Center(child: Text("Viewing Requested (Pending)", style: TextStyle(color: Colors.orange[800], fontWeight: FontWeight.bold))),
                                    )
                                  : OutlinedButton.icon(
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
                                            setState(() => _viewingStatus = 'PENDING'); // Instantly update UI
                                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Viewing requested!")));
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
                                    ),'''
text = text.replace(old_button, new_button)
DETAIL_FILE.write_text(text, encoding="utf-8")
print("✅ Patched listing_detail_screen.dart: Added smart viewing status button")

# ---------------------------------------------------------------- 2. Update Home Screen (Notification Badge)
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

# 2a. Add state for unread count
if "_unreadCount" not in text:
    text = text.replace(
        "class _HomeScreenState extends State<HomeScreen> {\n  late Future<List<dynamic>> _listings;",
        "class _HomeScreenState extends State<HomeScreen> {\n  late Future<List<dynamic>> _listings;\n  int _unreadCount = 0;"
    )
    
    # 2b. Add fetch method and call in initState
    text = text.replace(
        "  @override\n  void initState() {\n    super.initState();\n    _listings = ApiClient.getListings();\n  }",
        '''  @override
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
  }'''
    )

    # 2c. Wrap the notification icon in a Stack for the Badge
    old_icon = '''          IconButton(
            icon: Icon(Icons.notifications),
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => NotificationsScreen()));
            },
          ),'''
    new_icon = '''          Stack(
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
          ),'''
    text = text.replace(old_icon, new_icon)
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Added unread notification badge")

print("""
==================================================
🎉 PHASE 34 COMPLETE: SMART UX & BADGES!
==================================================

Go back to your terminal, quit ('q'), and restart the app.

### How to test the Seeker side:
1. Log in as seeker@nyumbalink.com.
2. Open a property and click "Request Viewing". Pick a date.
3. The button will instantly turn orange and say "Viewing Requested (Pending)".
4. If you go back and re-open the property, it will still be orange (proving it saved to the database).

### How to test the Landlord side:
1. Log in as landlord@nyumbalink.com.
2. On the Home screen, look at the Bell icon. It will have a red badge with a `1`.
3. Go to Profile -> My Properties -> Calendar Icon to approve it.
4. Go back to the Home screen, and the badge will disappear!
""")