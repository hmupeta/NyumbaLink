import 'package:flutter/material.dart';

class TermsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Terms & Conditions"), backgroundColor: Color(0xFF059669)),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("1. Platform Role", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
            SizedBox(height: 8),
            Text(
              "NyumbaLink is a digital marketplace designed to connect property seekers with landlords and agents in Zambia. "
              "We do not own, manage, or control any of the properties listed on this platform. All transactions, including rental payments and security deposits, are processed directly between the tenant and the landlord.",
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
            SizedBox(height: 24),
            Text("2. Limitation of Liability", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
            SizedBox(height: 8),
            Text(
              "While we strive to verify landlords and listings, NyumbaLink Platform Admins cannot be held liable for any disputes, damages, or losses arising from dealings between users. Users are encouraged to exercise due diligence, verify property ownership, and visit properties in person before making any payments.",
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
            SizedBox(height: 24),
            Text("3. Mobile Money Integration", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
            SizedBox(height: 8),
            Text(
              "Payments (Rent, Deposits, Contact Unlocks) are facilitated via secure Mobile Money gateways (MTN, Airtel, Zamtel). NyumbaLink does not store your mobile money PINs. Payment routing is handled securely by our integration partners.",
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
            SizedBox(height: 24),
            Text("4. Verification", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
            SizedBox(height: 8),
            Text(
              "A 'Verified' badge indicates that the landlord has submitted valid identification and property documents to the platform. However, verification does not replace the need for tenants to physically inspect the property.",
              style: TextStyle(fontSize: 15, height: 1.5),
            ),
            SizedBox(height: 40),
            Center(child: Text("© 2026 NyumbaLink. All rights reserved.", style: TextStyle(color: Colors.grey))),
          ],
        ),
      ),
    );
  }
}
