import 'package:intl/intl.dart';

import 'package:flutter/material.dart';
import 'api_client.dart';
import 'landlord_dashboard_screen.dart';
import 'main_layout.dart';
import 'lease_agreement_screen.dart';
import 'landlord_profile_screen.dart';
import 'listing_detail_screen.dart';

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

  void _handleNotificationTap(BuildContext context, String? link) {
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
              );
            },
          );
        },
      ),
    );
  }
}
