#!/usr/bin/env python3
"""NyumbaLink Phase 49: Mobile Lease Agreements & Digital Signatures."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getLeaseDetails" not in text:
    new_methods = '''
  // --- Lease Agreements ---
  static Future<Map<String, dynamic>> getLeaseDetails(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/leases/$id/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load lease');
  }

  static Future<Map<String, dynamic>> generateLeaseAgreement(String id) async {
    final res = await http.post(Uri.parse('$baseUrl/leases/$id/generate_agreement/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to generate agreement');
  }

  static Future<Map<String, dynamic>> signLease(String id) async {
    final res = await http.post(Uri.parse('$baseUrl/leases/$id/sign/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to sign lease');
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added lease agreement methods")

# ----------------------------------------------------------------
# 2. Create Lease Agreement Screen
# ----------------------------------------------------------------
LEASE_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';

class LeaseAgreementScreen extends StatefulWidget {
  final String leaseId;
  LeaseAgreementScreen({required this.leaseId});

  @override
  _LeaseAgreementScreenState createState() => _LeaseAgreementScreenState();
}

class _LeaseAgreementScreenState extends State<LeaseAgreementScreen> {
  late Future<Map<String, dynamic>> _leaseFuture;
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _loadLease();
  }

  void _loadLease() {
    setState(() {
      _leaseFuture = ApiClient.getLeaseDetails(widget.leaseId);
    });
  }

  void _generate() async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.generateLeaseAgreement(widget.leaseId);
      _loadLease();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  void _sign() async {
    setState(() => _isProcessing = true);
    try {
      final res = await ApiClient.signLease(widget.leaseId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res['status'] == 'fully_signed' ? "Contract Finalized!" : "Signature recorded. Waiting for other party."),
          backgroundColor: Colors.green,
        ));
        _loadLease();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(title: Text("Lease Agreement"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _leaseFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading lease"));

          final lease = snapshot.data!;
          final agreementText = lease['agreement_text'] as String?;
          final isLandlord = auth.user?['id'] == lease['landlord'];
          final isTenant = auth.user?['email'].toString().toLowerCase() == lease['tenant_email'].toString().toLowerCase();
          
          final landlordSigned = lease['landlord_signed'] ?? false;
          final tenantSigned = lease['tenant_signed'] ?? false;
          final bothSigned = landlordSigned && tenantSigned;
          final userSigned = isLandlord ? landlordSigned : tenantSigned;

          return SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(lease['property_name'], style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                Text("Tenant: ${lease['tenant_name']}", style: TextStyle(color: Colors.grey[600])),
                Divider(height: 32),

                if (agreementText == null || agreementText.isEmpty) ...[
                  Center(
                    child: Column(
                      children: [
                        Icon(Icons.description, size: 60, color: Colors.grey[400]),
                        SizedBox(height: 16),
                        Text("No agreement generated yet.", style: TextStyle(color: Colors.grey[600])),
                        SizedBox(height: 24),
                        if (isLandlord)
                          ElevatedButton(
                            onPressed: _isProcessing ? null : _generate,
                            style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(200, 50)),
                            child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Generate Agreement"),
                          )
                        else
                          Text("Waiting for landlord to generate the document.", style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  )
                ] else ...[
                  Container(
                    padding: EdgeInsets.all(16),
                    decoration: BoxDecoration(color: Colors.grey[50], border: Border.all(color: Colors.grey[300]!), borderRadius: BorderRadius.circular(8)),
                    child: Text(agreementText, style: TextStyle(height: 1.6, fontSize: 14)),
                  ),
                  SizedBox(height: 24),

                  // Signatures Status
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildSignatureStatus("Landlord", landlordSigned),
                      _buildSignatureStatus("Tenant", tenantSigned),
                    ],
                  ),
                  SizedBox(height: 24),

                  if (bothSigned)
                    Container(
                      padding: EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                      child: Row(
                        children: [
                          Icon(Icons.check_circle, color: Colors.green),
                          SizedBox(width: 12),
                          Expanded(child: Text("Contract Finalized. Property is now marked as OCCUPIED.", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                        ],
                      ),
                    )
                  else if (isLandlord || isTenant)
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: userSigned || _isProcessing ? null : _sign,
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700]),
                        child: _isProcessing 
                          ? CircularProgressIndicator(color: Colors.white) 
                          : Text(userSigned ? "You have signed" : "Digitally Sign Agreement"),
                      ),
                    )
                ]
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSignatureStatus(String role, bool isSigned) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isSigned ? Colors.green[50] : Colors.orange[50],
        border: Border.all(color: isSigned ? Colors.green : Colors.orange),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        children: [
          Text(role, style: TextStyle(fontWeight: FontWeight.bold)),
          Text(isSigned ? "✓ Signed" : "Pending", style: TextStyle(color: isSigned ? Colors.green : Colors.orange)),
        ],
      ),
    );
  }
}
'''
(LIB / "lease_agreement_screen.dart").write_text(LEASE_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created lease_agreement_screen.dart")

# ----------------------------------------------------------------
# 3. Link from Tenant Portal
# ----------------------------------------------------------------
TENANT_PORTAL = LIB / "tenant_portal_screen.dart"
text = TENANT_PORTAL.read_text(encoding="utf-8")

if "LeaseAgreementScreen" not in text:
    text = text.replace(
        "import 'api_client.dart';",
        "import 'api_client.dart';\nimport 'lease_agreement_screen.dart';"
    )
    
    # Add a button above the maintenance button
    old_button = '''                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _showMaintenanceDialog(lease['id']),'''
                          
    new_button = '''                      SizedBox(
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
                          onPressed: () => _showMaintenanceDialog(lease['id']),'''
                          
    text = text.replace(old_button, new_button)
    TENANT_PORTAL.write_text(text, encoding="utf-8")
    print("✅ Patched tenant_portal_screen.dart: Added Lease link")

# ----------------------------------------------------------------
# 4. Link from Landlord Dashboard (Tenants Tab)
# ----------------------------------------------------------------
TENANTS_TAB = LIB / "tenants_tab.dart"
text = TENANTS_TAB.read_text(encoding="utf-8")

if "LeaseAgreementScreen" not in text:
    text = text.replace(
        "import 'api_client.dart';",
        "import 'api_client.dart';\nimport 'lease_agreement_screen.dart';"
    )
    
    # Add an action button to the ExpansionTile
    old_expansion = '''                children: records.map((record) {'''
    new_expansion = '''                children: [
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
                  ...records.map((record) {'''
                  
    text = text.replace(old_expansion, new_expansion)
    TENANTS_TAB.write_text(text, encoding="utf-8")
    print("✅ Patched tenants_tab.dart: Added Lease link for Landlord")

print("""
==================================================
🎉 PHASE 49 COMPLETE: MOBILE LEASE SIGNING
==================================================

Go back to your terminal, quit ('q'), and restart the app.

### How to test:
1. Log in as the **Tenant** (`seeker@nyumbalink.com`).
2. Go to Profile -> **My Tenancy**.
3. Click the new **"View & Sign Lease Agreement"** button. (You will see "Waiting for Landlord" if they haven't generated it).
4. Log in as the **Landlord** (`landlord@nyumbalink.com`).
5. Go to Profile -> My Properties -> Tenants tab.
6. Expand the tenant card and click **"Manage Lease Agreement"**.
7. Click **Generate Agreement**, then **Digitally Sign**.
8. Log back in as the Tenant, open the lease, and click **Digitally Sign**.
9. The contract is finalized, and the property is marked `OCCUPIED`!
""")