#!/usr/bin/env python3
"""Fixes the Flutter login navigation error."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

LOGIN_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'home_screen.dart'; // Ensure HomeScreen is imported

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;

  void _submit() async {
    setState(() => _loading = true);
    try {
      await Provider.of<AuthProvider>(context, listen: false).login(_emailCtrl.text, _passCtrl.text);
      
      // FIX: Use MaterialPageRoute instead of pushReplacementNamed('/home')
      if (mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => HomeScreen()),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
    if (mounted) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text("NyumbaLink", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
              SizedBox(height: 40),
              TextField(controller: _emailCtrl, decoration: InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
              SizedBox(height: 16),
              TextField(controller: _passCtrl, decoration: InputDecoration(labelText: 'Password', border: OutlineInputBorder()), obscureText: true),
              SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                  child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Login"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
'''

(LIB / "login_screen.dart").write_text(LOGIN_SCREEN.strip() + "\n", encoding="utf-8")

print("""
==================================================
🎉 LOGIN NAVIGATION FIXED!
==================================================

Go back to your Flutter terminal and fully restart the app (press 'q', then run again).

Run: flutter run -d chrome --web-port 5173

1. You will land on the Home screen immediately.
2. Click "Login" in the top bar.
3. Enter: seeker@nyumbalink.com / SeekerPassword123!
4. The app will successfully log in, close the login screen, and bring you back to the Home screen.
5. You will now see your profile icon in the top right, and the "Message Landlord" button on properties will work.
""")