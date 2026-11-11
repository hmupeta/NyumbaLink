import 'package:flutter/material.dart';
import 'api_client.dart';

class ForgotPasswordScreen extends StatefulWidget {
  @override
  _ForgotPasswordScreenState createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _emailCtrl = TextEditingController();
  bool _submitted = false;
  bool _loading = false;
  String? _error;

  void _submit() async {
    if (_emailCtrl.text.trim().isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      await ApiClient.requestPasswordReset(_emailCtrl.text.trim());
      setState(() { _submitted = true; });
    } catch (e) {
      setState(() { _error = e.toString(); });
    }
    setState(() { _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_submitted) {
      return Scaffold(
        appBar: AppBar(title: Text("Forgot Password"), backgroundColor: Color(0xFF059669)),
        body: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.mark_email_read, size: 80, color: Colors.green),
              SizedBox(height: 16),
              Text("Check your email", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Text("We've sent a password reset link to ${_emailCtrl.text}. Open the link on a device with a browser to reset your password.",
                textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
              SizedBox(height: 32),
              TextButton(onPressed: () => Navigator.pop(context), child: Text("Back to Login")),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text("Forgot Password"), backgroundColor: Color(0xFF059669)),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Reset your password", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text("Enter the email address associated with your account.", style: TextStyle(color: Colors.grey)),
            SizedBox(height: 24),
            if (_error != null) Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(color: Colors.red[50], borderRadius: BorderRadius.circular(8)),
              child: Text(_error!, style: TextStyle(color: Colors.red[800])),
            ),
            SizedBox(height: 12),
            TextField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(labelText: "Email", border: OutlineInputBorder()),
            ),
            SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _loading ? null : _submit,
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Send Reset Link"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
