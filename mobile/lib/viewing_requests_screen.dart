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
