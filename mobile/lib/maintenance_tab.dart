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
