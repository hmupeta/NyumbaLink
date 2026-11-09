import 'package:intl/intl.dart';

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
