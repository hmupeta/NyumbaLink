import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'login_screen.dart';
import 'landlord_dashboard_screen.dart';

class ProfileScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(title: Text("My Profile"), backgroundColor: Color(0xFF059669)),
      body: auth.user == null
        ? Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text("You are not logged in."),
                SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                  child: Text("Log In"),
                  style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                )
              ],
            ),
          )
        : Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 40,
                  backgroundColor: Color(0xFF059669),
                  child: Text(
                    auth.user!['first_name']?.isNotEmpty == true ? auth.user!['first_name'][0].toUpperCase() : 'U',
                    style: TextStyle(fontSize: 32, color: Colors.white),
                  ),
                ),
                SizedBox(height: 16),
                Text("${auth.user!['first_name']} ${auth.user!['last_name'] ?? ''}", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                Text(auth.user!['email'], style: TextStyle(color: Colors.grey)),
                Divider(height: 40),
                ListTile(
                  leading: Icon(Icons.home_work, color: Color(0xFF059669)),
                  title: Text("My Properties (Landlord)"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    Navigator.push(context, MaterialPageRoute(builder: (_) => LandlordDashboardScreen()));
                  },
                ),
                ListTile(
                  leading: Icon(Icons.verified_user, color: Color(0xFF059669)),
                  title: Text("Verification"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Verification coming soon to mobile!")));
                  },
                ),
                ListTile(
                  leading: Icon(Icons.logout, color: Colors.red),
                  title: Text("Logout", style: TextStyle(color: Colors.red)),
                  onTap: () {
                    auth.logout();
                  },
                ),
              ],
            ),
          ),
    );
  }
}
