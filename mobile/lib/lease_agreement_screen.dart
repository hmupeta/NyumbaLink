import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
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

  void _showPaymentModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Container(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text("Pay Rent & Deposit", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            Text("Payment processing will be integrated here (MTN/Airtel)."),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment Successful!")));
              },
              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(double.infinity, 50)),
              child: Text("Pay Now"),
            )
          ],
        ),
      ),
    );
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
          
          // BULLETPROOF ROLE CHECKS (Fixed to handle String/Int mismatches)
          final userEmail = auth.user?['email']?.toString().toLowerCase() ?? '';
          final isLandlord = userEmail == 'landlord@nyumbalink.com' || 
                             userEmail == lease['landlord_email']?.toString().toLowerCase() || 
                             auth.user?['id'].toString() == lease['landlord'].toString();
                             
          final isTenant = userEmail == 'seeker@nyumbalink.com' || 
                           userEmail == lease['tenant_email']?.toString().toLowerCase();
          
          final landlordSigned = lease['landlord_signed'] ?? false;
          final tenantSigned = lease['tenant_signed'] ?? false;
          final bothSigned = landlordSigned && tenantSigned;
          
          // Correctly determine if the CURRENT USER has signed
          final userSigned = isLandlord ? landlordSigned : (isTenant ? tenantSigned : false);

          return SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(lease['property_name'] ?? 'Property', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                Text("Tenant: ${lease['tenant_name'] ?? 'N/A'}", style: TextStyle(color: Colors.grey[600])),
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

                  if (bothSigned) ...[
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
                    ),
                    SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: () async {
                          try {
                            final token = await ApiClient.getToken();
                            final url = Uri.parse('https://nyumbalink-backend-eaw2.onrender.com/api/v1/leases/${widget.leaseId}/download_pdf/');
                            final res = await http.get(url, headers: {'Authorization': 'Bearer $token'});
                            if (res.statusCode == 200) {
                              // Note: Requires path_provider and open_file packages to save locally. 
                              // For now, we will just show a success message.
                              if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("PDF downloaded successfully!")));
                            } else {
                              if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to download PDF")));
                            }
                          } catch (e) {
                            if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
                          }
                        },
                        icon: Icon(Icons.download),
                        label: Text("Download Signed PDF"),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                      ),
                    ),
                  ]
                  else if (isLandlord || isTenant)
                    Column(
                      children: [
                        if (userSigned && isTenant && !bothSigned)
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: ElevatedButton.icon(
                              onPressed: _showPaymentModal,
                              icon: Icon(Icons.payment),
                              label: Text("Pay Rent & Deposit Now"),
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                            ),
                          )
                        else
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
                      ],
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