import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';

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
      
      // FIX: Check if we can pop. If not (because we were pushed as root by the 401 handler),
      // we must push the MainLayout instead.
      if (mounted) {
        if (Navigator.canPop(context)) {
          Navigator.pop(context);
        } else {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => MainLayout()),
          );
        }
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
              Column(
  children: [
    Image.asset("assets/images/logo.png", height: 120),
    SizedBox(height: 16),
    Text("NyumbaLink", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
  ],
),
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
