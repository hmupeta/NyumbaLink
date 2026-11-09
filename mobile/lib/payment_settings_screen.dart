import 'package:flutter/material.dart';
import 'api_client.dart';

class PaymentSettingsScreen extends StatefulWidget {
  @override
  _PaymentSettingsScreenState createState() => _PaymentSettingsScreenState();
}

class _PaymentSettingsScreenState extends State<PaymentSettingsScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  String _activeTab = 'MTN';

  final _mtnUserCtrl = TextEditingController();
  final _mtnKeyCtrl = TextEditingController();
  final _airtelIdCtrl = TextEditingController();
  final _airtelSecretCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final data = await ApiClient.getPaymentSettings();
      _mtnUserCtrl.text = data['mtn_api_user'] ?? '';
      _airtelIdCtrl.text = data['airtel_client_id'] ?? '';
      if (mounted) setState(() => _isLoading = false);
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _save() async {
    setState(() => _isSaving = true);
    try {
      await ApiClient.updatePaymentSettings({
        'mtn_api_user': _mtnUserCtrl.text,
        'mtn_api_key': _mtnKeyCtrl.text,
        'airtel_client_id': _airtelIdCtrl.text,
        'airtel_client_secret': _airtelSecretCtrl.text,
      });
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment settings saved!")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to save settings")));
    }
    if (mounted) setState(() => _isSaving = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return Scaffold(body: Center(child: CircularProgressIndicator()));

    return Scaffold(
      appBar: AppBar(title: Text("Payment Integrations"), backgroundColor: Color(0xFF059669)),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Connect your merchant accounts so tenants can pay you directly.", style: TextStyle(color: Colors.grey[600])),
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
              TextField(controller: _mtnUserCtrl, decoration: InputDecoration(labelText: 'MTN API User', border: OutlineInputBorder())),
              SizedBox(height: 12),
              TextField(controller: _mtnKeyCtrl, decoration: InputDecoration(labelText: 'MTN API Key', border: OutlineInputBorder(), helperText: "Leave blank to keep existing key"), obscureText: true),
            ] else ...[
              TextField(controller: _airtelIdCtrl, decoration: InputDecoration(labelText: 'Airtel Client ID', border: OutlineInputBorder())),
              SizedBox(height: 12),
              TextField(controller: _airtelSecretCtrl, decoration: InputDecoration(labelText: 'Airtel Client Secret', border: OutlineInputBorder(), helperText: "Leave blank to keep existing secret"), obscureText: true),
            ],
            
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isSaving ? null : _save,
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: _isSaving ? CircularProgressIndicator(color: Colors.white) : Text("Save Settings"),
              ),
            ),
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
