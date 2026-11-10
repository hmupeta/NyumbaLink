#!/usr/bin/env python3
"""Adds Login button, Intro text, and Terms & Conditions to Flutter Home Screen."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Create Terms & Conditions Screen
# ----------------------------------------------------------------
TERMS_SCREEN = '''
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
'''
(LIB / "terms_screen.dart").write_text(TERMS_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created terms_screen.dart")

# ----------------------------------------------------------------
# 2. Update Home Screen
# ----------------------------------------------------------------
HOME_FILE = LIB / "home_screen.dart"
text = HOME_FILE.read_text(encoding="utf-8")

# Imports
if "terms_screen.dart" not in text:
    text = text.replace(
        "import 'map_view.dart';",
        "import 'map_view.dart';\nimport 'terms_screen.dart';\nimport 'login_screen.dart';"
    )

# Add Login button to AppBar (only if user is not logged in)
if "auth.user == null" not in text:
    text = text.replace(
        "  @override\n  Widget build(BuildContext context) {\n    return Scaffold(",
        "  @override\n  Widget build(BuildContext context) {\n    final auth = Provider.of<AuthProvider>(context);\n    return Scaffold("
    )
    
    old_actions = '''        actions: [
          IconButton(
            icon: Icon(Icons.bookmark),'''
            
    new_actions = '''        actions: [
          if (auth.user == null)
            TextButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
              child: Text("Login", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
          IconButton(
            icon: Icon(Icons.bookmark),'''
    
    text = text.replace(old_actions, new_actions)

# Add Intro Card as the first item in the ListView
if "_buildIntroCard" not in text:
    # 1. Update the ListView builder logic
    old_list = '''                ListView.builder(
                  itemCount: listings.length,
                  itemBuilder: (context, index) {
                    final l = listings[index];'''
                    
    new_list = '''                ListView.builder(
                  itemCount: listings.length + 1, // +1 for the header
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return _buildIntroCard(context);
                    }
                    final l = listings[index - 1];'''
                    
    text = text.replace(old_list, new_list)

    # 2. Add the _buildIntroCard method at the end of the state class
    intro_method = '''
  Widget _buildIntroCard(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: 16),
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.green[50],
        border: Border(bottom: BorderSide(color: Colors.green[200]!, width: 2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Find your place. Connect your world.",
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF059669)),
          ),
          SizedBox(height: 8),
          Text(
            "NyumbaLink bridges the gap between tenants and landlords in Zambia. Browse verified properties, chat directly with landlords, and pay rent or deposits securely via MTN, Airtel, or Zamtel Mobile Money.",
            style: TextStyle(fontSize: 14, height: 1.5, color: Colors.grey[800]),
          ),
          SizedBox(height: 12),
          GestureDetector(
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => TermsScreen())),
            child: Text(
              "Read our Terms & Conditions",
              style: TextStyle(color: Colors.blue[700], fontWeight: FontWeight.bold, decoration: TextDecoration.underline),
            ),
          ),
        ],
      ),
    );
  }
'''
    # Insert before the final closing brace of the class
    text = text[::-1].replace("}", intro_method[::-1], 1)[::-1]
    
    HOME_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched home_screen.dart: Added Intro Card, Login button, and Terms link")
else:
    print("ℹ️ Intro card already exists in home_screen.dart")

print("""
==================================================
🎉 PHASE 47 COMPLETE: WELCOME SCREEN & TERMS
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. On the Home screen, you will now see a **Login** button in the top right.
2. Before the first property, there is a green **Welcome Card** explaining the platform and Mobile Money integration.
3. Clicking **"Read our Terms & Conditions"** opens a legal screen that protects the platform admin from liability.
""")