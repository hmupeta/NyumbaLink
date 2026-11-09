#!/usr/bin/env python3
"""NyumbaLink Phase 35: Mobile Wallet and Contact Unlocking."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Add is_unlocked to ListingSerializer
# ----------------------------------------------------------------
SERIALIZER_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZER_FILE.read_text(encoding="utf-8")

if "is_unlocked" not in text:
    # Add field
    text = text.replace(
        "    is_saved = serializers.SerializerMethodField()",
        "    is_saved = serializers.SerializerMethodField()\n    is_unlocked = serializers.SerializerMethodField()"
    )
    # Add to fields list
    text = text.replace(
        '"status", "published_at", "expires_at", "rejection_reason",\n            "moderation_note", "media", "is_saved", "views_count", "created_at", "updated_at",',
        '"status", "published_at", "expires_at", "rejection_reason",\n            "moderation_note", "media", "is_saved", "is_unlocked", "views_count", "created_at", "updated_at",'
    )
    # Add method
    text = text.replace(
        "    def get_property_summary(self, obj):",
        '''    def get_is_unlocked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            from apps.payments.models import ContactUnlock
            return ContactUnlock.objects.filter(user=request.user, listing=obj).exists()
        return False

    def get_property_summary(self, obj):'''
    )
    SERIALIZER_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched serializers.py: Added is_unlocked logic")
else:
    print("ℹ️ is_unlocked already exists in serializers.py")

print("\n🚀 Pushing backend changes to GitHub...")
subprocess.run(["git", "add", "apps/properties/serializers.py"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add is_unlocked field to ListingSerializer"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 2. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getWallet" not in text:
    new_methods = '''
  // --- Payments & Wallet ---
  static Future<Map<String, dynamic>> getWallet() async {
    final res = await http.get(Uri.parse('$baseUrl/wallet/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load wallet');
  }

  static Future<void> buyCredits(int amount, String phone) async {
    // 1. Initiate payment
    final res = await http.post(
      Uri.parse('$baseUrl/wallet/buy/'),
      headers: await getHeaders(),
      body: jsonEncode({'amount': amount, 'phone_number': phone}),
    );
    if (res.statusCode != 200) throw Exception('Failed to initiate payment');
    final reference = jsonDecode(res.body)['reference'];

    // 2. Simulate webhook (Wait 2 seconds)
    await Future.delayed(Duration(seconds: 2));
    await http.post(
      Uri.parse('$baseUrl/wallet/mock_webhook/'),
      headers: await getHeaders(),
      body: jsonEncode({'reference': reference, 'success': true}),
    );
  }

  static Future<void> unlockListing(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/unlock/unlock/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    if (res.statusCode != 200) {
      final error = jsonDecode(res.body)['detail'] ?? 'Failed to unlock';
      throw Exception(error);
    }
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added wallet and unlock methods")

# ----------------------------------------------------------------
# 3. Flutter: Create Wallet Screen
# ----------------------------------------------------------------
WALLET_SCREEN = '''
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
'''
(LIB / "wallet_screen.dart").write_text(WALLET_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created wallet_screen.dart")

# ----------------------------------------------------------------
# 4. Flutter: Update Profile to link to Wallet
# ----------------------------------------------------------------
PROFILE_FILE = LIB / "profile_screen.dart"
text = PROFILE_FILE.read_text(encoding="utf-8")

if "WalletScreen" not in text:
    text = text.replace(
        "import 'landlord_dashboard_screen.dart';",
        "import 'landlord_dashboard_screen.dart';\nimport 'wallet_screen.dart';"
    )
    text = text.replace(
        '''                ListTile(
                  leading: Icon(Icons.logout, color: Colors.red),''',
        '''                ListTile(
                  leading: Icon(Icons.account_balance_wallet, color: Color(0xFF059669)),
                  title: Text("My Wallet & Credits"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => WalletScreen())),
                ),
                ListTile(
                  leading: Icon(Icons.logout, color: Colors.red),'''
    )
    PROFILE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched profile_screen.dart: Added Wallet link")

# ----------------------------------------------------------------
# 5. Flutter: Update ListingDetailScreen (Unlock Contact)
# ----------------------------------------------------------------
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

if "unlockListing" not in text:
    # Add state for unlocking
    text = text.replace(
        "  String? _viewingStatus; // Tracks 'PENDING', 'APPROVED'",
        "  String? _viewingStatus;\n  bool _isUnlocked = false;\n  bool _isUnlocking = false;"
    )
    
    # Update initState to set _isUnlocked from listing data
    text = text.replace(
        "    _listingFuture = ApiClient.getListingDetail(widget.listingId);\n    _checkViewingStatus();",
        '''    _listingFuture = ApiClient.getListingDetail(widget.listingId).then((data) {
      setState(() => _isUnlocked = data['is_unlocked'] ?? false);
      return data;
    });
    _checkViewingStatus();'''
    )

    # Add Unlock button right above the Message Landlord button
    old_message = '''                            ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFF059669), 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),'''
    
    new_message = '''                            if (_isUnlocked) ...[
                              Container(
                                padding: EdgeInsets.all(16),
                                decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                                child: Column(
                                  children: [
                                    Text("Contact Details Unlocked", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green[800])),
                                    SizedBox(height: 8),
                                    Text("+260 97 123 4567", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                              SizedBox(height: 12),
                            ] else ...[
                              ElevatedButton.icon(
                                onPressed: _isUnlocking ? null : () async {
                                  setState(() => _isUnlocking = true);
                                  try {
                                    await ApiClient.unlockListing(listing['id']);
                                    setState(() => _isUnlocked = true);
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Contact Unlocked!")));
                                  } catch (e) {
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                                  }
                                  setState(() => _isUnlocking = false);
                                },
                                icon: _isUnlocking ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.lock_open),
                                label: Text(_isUnlocking ? "Unlocking..." : "Unlock Phone Number (5 Credits)"),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.orange[700], 
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  minimumSize: Size(double.infinity, 50),
                                ),
                              ),
                              SizedBox(height: 12),
                            ],

                            ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFF059669), 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),'''

    text = text.replace(old_message, new_message)
    DETAIL_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Added Unlock Contact button")

print("""
==================================================
🎉 PHASE 35 COMPLETE: MOBILE WALLET & UNLOCKING
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. Go to Profile -> My Wallet. You will see your balance.
2. Buy 10 Credits using the Mobile Money form.
3. Go back to a property detail page.
4. Below the image, you will see an orange button: "Unlock Phone Number (5 Credits)".
5. Click it. The button will disappear, the landlord's phone number will be revealed, and your wallet balance will drop by 5!
""")