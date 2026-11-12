import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'api_client.dart';
import 'momo_payment_modal.dart';
import 'lease_agreement_screen.dart';

class TenantPortalScreen extends StatefulWidget {
  @override
  _TenantPortalScreenState createState() => _TenantPortalScreenState();
}

class _TenantPortalScreenState extends State<TenantPortalScreen> {
  Future<void> _loadViewings() async {
    // TODO: Implement actual fetching of viewings from API
    print("Viewings refreshed");
  }

  late Future<List<dynamic>> _leasesFuture;

  @override
  void initState() {
    super.initState();
    _leasesFuture = ApiClient.getMyTenancy();
  }

  void _showMaintenanceDialog(String leaseId) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    String priority = 'MEDIUM';

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setStateDialog) {
          return AlertDialog(
            title: Text("Report an Issue"),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: titleCtrl,
                    decoration: InputDecoration(labelText: "Issue Title", border: OutlineInputBorder()),
                  ),
                  SizedBox(height: 12),
                  TextField(
                    controller: descCtrl,
                    decoration: InputDecoration(labelText: "Description", border: OutlineInputBorder()),
                    maxLines: 3,
                  ),
                  SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: priority,
                    decoration: InputDecoration(labelText: "Priority", border: OutlineInputBorder()),
                    items: ['LOW', 'MEDIUM', 'HIGH'].map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                    onChanged: (val) => setStateDialog(() => priority = val!),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: Text("Cancel")),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                onPressed: () async {
                  if (titleCtrl.text.isEmpty || descCtrl.text.isEmpty) return;
                  Navigator.pop(context);
                  try {
                    await ApiClient.createMaintenanceRequest({
                      'title': titleCtrl.text,
                      'description': descCtrl.text,
                      'priority': priority,
                      'lease': leaseId,
                    });
                    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Issue reported to landlord!")));
                  } catch (e) {
                    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                },
                child: Text("Submit"),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("My Tenancy"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _leasesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading tenancy"));

          final leases = snapshot.data!;
          if (leases.isEmpty) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  "You have no active leases. If you are a tenant, please ask your landlord to add you.",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
              ),
            );
          }

          return ListView.builder(
            padding: EdgeInsets.all(16),
            itemCount: leases.length,
            itemBuilder: (context, index) {
              final lease = leases[index];
              final records = lease['rent_records'] as List<dynamic>? ?? [];
              final pending = records.where((r) => r['status'] == 'PENDING').toList();

              return Card(
                margin: EdgeInsets.only(bottom: 16),
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(lease['property_name'], style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      SizedBox(height: 4),
                      Text("Monthly Rent: ${lease['monthly_rent']} ZMW", style: TextStyle(color: Colors.grey[700])),
                      SizedBox(height: 4),
                      Text("Lease Ends: ${DateFormat('MMM d, yyyy').format(DateTime.parse(lease['end_date']))}", style: TextStyle(color: Colors.grey[600], fontSize: 12)),
                      
                      Divider(height: 32),
                      
                      Text("Rent Schedule", style: TextStyle(fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      ...records.take(6).map((r) {
                        final isPaid = r['status'] == 'PAID';
                        return ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(isPaid ? Icons.check_circle : Icons.schedule, color: isPaid ? Colors.green : Colors.orange),
                          title: Text(DateFormat('MMM yyyy').format(DateTime.parse(r['due_date']))),
                          subtitle: Text("K${r['amount']}"),
                          trailing: isPaid 
                          ? Text("Paid", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green))
                          : TextButton(
                              onPressed: () {
                                showModalBottomSheet(
                                  context: context,
                                  isScrollControlled: true,
                                  builder: (context) => MomoPaymentModal(
                                    rentRecordId: r['id'],
                                    amount: double.parse(r['amount'].toString()),
                                    onSuccess: () {
                                      Navigator.pop(context);
                                      _loadViewings(); // refresh schedule
                                    },
                                    onClose: () {
                                      Navigator.pop(context);
                                      _loadViewings();
                                    },
                                  ),
                                );
                              },
                              child: Text("Pay Now", style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                            ),
                        );
                      }),
                      
                      SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LeaseAgreementScreen(leaseId: lease['id']))),
                          icon: Icon(Icons.description),
                          label: Text("View & Sign Lease Agreement"),
                          style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                        ),
                      ),
                      SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _showMaintenanceDialog(lease['id']),
                          icon: Icon(Icons.build, color: Colors.blue),
                          label: Text("Report Maintenance Issue", style: TextStyle(color: Colors.blue)),
                          style: OutlinedButton.styleFrom(side: BorderSide(color: Colors.blue)),
                        ),
                      ),
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
