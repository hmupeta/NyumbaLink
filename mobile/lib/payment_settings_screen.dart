import 'package:flutter/material.dart';
import 'api_client.dart';

class PaymentSettingsScreen extends StatefulWidget {
  @override
  _PaymentSettingsScreenState createState() => _PaymentSettingsScreenState();
}

class _PaymentSettingsScreenState extends State<PaymentSettingsScreen> {
  bool _isLoading = true;
  bool _isProcessing = false;
  String _activeTab = 'MTN';
  Map<String, dynamic> _settings = {};

  final _primaryKeyCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final data = await ApiClient.getPaymentSettings();
      if (mounted) setState(() { _settings = data; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _generateMTN() async {
    if (_primaryKeyCtrl.text.isEmpty) return;
    setState(() => _isProcessing = true);
    try {
      final res = await ApiClient.post('/payment-settings/generate_mtn_user/', {
        'mtn_subscription_key': _primaryKeyCtrl.text.trim()
      });
      await _loadSettings();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("API User Generated Successfully!")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  Future<void> _testMTN() async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.post('/payment-settings/test_mtn_connection/', {});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Connection Successful! MTN Sandbox is reachable.")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return Scaffold(body: Center(child: CircularProgressIndicator()));

    final bool isMTNConnected = _settings['mtn_api_user'] != null && _settings['mtn_api_user'].toString().isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: Text("Payment Integrations"), backgroundColor: Color(0xFF059669)),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Connect your merchant accounts to receive rent and deposits directly from tenants.", style: TextStyle(color: Colors.grey[600])),
            SizedBox(height: 16),
            Row(
              children: [
                _buildTab("MTN", "MTN MoMo"),
                SizedBox(width: 8),
                _buildTab("AIRTEL", "Airtel Money"),
              ],
            ),
            SizedBox(height: 24),
            
            if (_activeTab == 'MTN') ...[
              if (isMTNConnected)
                Container(
                  padding: EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("MTN MoMo is Connected", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green[800], fontSize: 18)),
                      SizedBox(height: 8),
                      Text("API User: ${_settings['mtn_api_user']}", style: TextStyle(color: Colors.green[900])),
                      SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isProcessing ? null : _testMTN,
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                          child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Test Connection"),
                        ),
                      )
                    ],
                  ),
                )
              else
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text("Connect MTN MoMo (Sandbox)", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    Text("Enter your Primary Key (Subscription Key) from the MTN Developer Portal. We will automatically generate your API User and API Key.", style: TextStyle(color: Colors.grey)),
                    SizedBox(height: 16),
                    TextField(
                      controller: _primaryKeyCtrl,
                      decoration: InputDecoration(labelText: 'MTN Primary Key', border: OutlineInputBorder(), hintText: "e.g. 9b8a..."),
                    ),
                    SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isProcessing ? null : _generateMTN,
                      style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(double.infinity, 50)),
                      child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Generate API User & Key"),
                    ),
                  ],
                )
            ] else ...[
              Text("Airtel Money Integration coming soon.", style: TextStyle(color: Colors.grey)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTab(String id, String label) {
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeTab = id),
        child: Container(
          padding: EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: _activeTab == id ? Color(0xFF059669) : Colors.grey[200],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(color: _activeTab == id ? Colors.white : Colors.black87, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ),
    );
  }
}
