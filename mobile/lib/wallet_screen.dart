import 'package:flutter/material.dart';
import 'api_client.dart';

class WalletScreen extends StatefulWidget {
  @override
  _WalletScreenState createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  int _balance = 0;
  bool _isLoading = true;
  bool _isBuying = false;
  final _phoneCtrl = TextEditingController(text: "0977123456");
  int _selectedAmount = 10;

  @override
  void initState() {
    super.initState();
    _loadWallet();
  }

  Future<void> _loadWallet() async {
    try {
      final data = await ApiClient.getWallet();
      if (mounted) setState(() { _balance = data['balance']; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _buyCredits() async {
    setState(() => _isBuying = true);
    try {
      await ApiClient.buyCredits(_selectedAmount, _phoneCtrl.text);
      await _loadWallet(); // Refresh balance
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Successfully bought $_selectedAmount credits!")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment failed: $e")));
    }
    if (mounted) setState(() => _isBuying = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return Center(child: CircularProgressIndicator());

    return Scaffold(
      appBar: AppBar(title: Text("My Wallet"), backgroundColor: Color(0xFF059669)),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Color(0xFF059669),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  Text("Available Credits", style: TextStyle(color: Colors.white70, fontSize: 16)),
                  SizedBox(height: 8),
                  Text("$_balance", style: TextStyle(color: Colors.white, fontSize: 48, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            SizedBox(height: 32),
            Text("Buy Credits", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            DropdownButtonFormField<int>(
              value: _selectedAmount,
              decoration: InputDecoration(labelText: 'Amount', border: OutlineInputBorder()),
              items: [10, 20, 50].map((a) => DropdownMenuItem(value: a, child: Text("$a Credits"))).toList(),
              onChanged: (val) => setState(() => _selectedAmount = val!),
            ),
            SizedBox(height: 16),
            TextField(
              controller: _phoneCtrl,
              decoration: InputDecoration(labelText: 'Mobile Money Number', border: OutlineInputBorder()),
              keyboardType: TextInputType.phone,
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isBuying ? null : _buyCredits,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.black),
                child: _isBuying ? CircularProgressIndicator(color: Colors.white) : Text("Pay with Mobile Money"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
