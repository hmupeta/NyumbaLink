import 'package:flutter/material.dart';
import 'api_client.dart';
import 'chat_screen.dart';

class InboxScreen extends StatefulWidget {
  @override
  _InboxScreenState createState() => _InboxScreenState();
}

class _InboxScreenState extends State<InboxScreen> {
  late Future<List<dynamic>> _convsFuture;

  @override
  void initState() {
    super.initState();
    _convsFuture = ApiClient.getConversations();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Inbox"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _convsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Padding(padding: EdgeInsets.all(24), child: Text("Please log in to view your inbox.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey))));
          
          final convs = snapshot.data!;
          if (convs.isEmpty) return Center(child: Text("No messages yet."));

          return ListView.builder(
            itemCount: convs.length,
            itemBuilder: (context, index) {
              final c = convs[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Color(0xFF059669),
                  child: Icon(Icons.home, color: Colors.white),
                ),
                title: Text(c['listing_title'], maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text(c['last_message'] != null ? c['last_message']['body'] : 'No messages', maxLines: 1, overflow: TextOverflow.ellipsis),
                trailing: Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => ChatScreen(
                      conversationId: c['id'],
                      landlordName: c['landlord_email'] == c['landlord'] ? c['seeker_email'] : c['landlord_email'],
                    )),
                  ).then((_) => setState(() { _convsFuture = ApiClient.getConversations(); }));
                },
              );
            },
          );
        },
      ),
    );
  }
}
