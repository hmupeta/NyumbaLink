#!/usr/bin/env python3
"""Rewrites tenants_tab.dart with clean syntax and the Lease Agreement button."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "tenants_tab.dart"

NEW_TENANTS_TAB = '''
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'api_client.dart';
import 'lease_agreement_screen.dart';

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
                children: [
                  // Lease Agreement button
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                    child: SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LeaseAgreementScreen(leaseId: lease['id']))),
                        icon: Icon(Icons.description, color: Color(0xFF059669)),
                        label: Text("Manage Lease Agreement", style: TextStyle(color: Color(0xFF059669))),
                        style: OutlinedButton.styleFrom(side: BorderSide(color: Color(0xFF059669))),
                      ),
                    ),
                  ),

                  // Rent records
                  ...records.map((record) {
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
                ],
              ),
            );
          },
        );
      },
    );
  }
}
'''

FILE.write_text(NEW_TENANTS_TAB.strip() + "\n", encoding="utf-8")
print("✅ Rewrote tenants_tab.dart with clean syntax")

print("""
==================================================
🎉 SYNTAX FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.

The Tenants tab will now load properly, and you can expand a tenant to see:
1. **Manage Lease Agreement** button at the top
2. The rent schedule below
""")