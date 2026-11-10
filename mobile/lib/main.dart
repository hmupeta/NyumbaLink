import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'auth_provider.dart';
import 'main_layout.dart';
import 'api_client.dart';
import 'login_screen.dart';

// Global keys allow us to navigate or show SnackBars from anywhere in the app
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

void main() {
  // Set up the global 401 handler
  ApiClient.onUnauthorized = () {
    final context = navigatorKey.currentContext;
    if (context != null) {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      
      // ONLY trigger the session expired redirect if the user was previously logged in.
      // If they are a guest, 401s are expected for protected endpoints.
      if (auth.user != null) {
        auth.logout();
        
        scaffoldMessengerKey.currentState?.showSnackBar(
          SnackBar(
            content: Text("Session expired. Please log in again."),
            backgroundColor: Colors.red,
          )
        );
        
        navigatorKey.currentState?.pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => LoginScreen()),
          (Route<dynamic> route) => false,
        );
      }
    }
  };

  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NyumbaLink',
      navigatorKey: navigatorKey,
      scaffoldMessengerKey: scaffoldMessengerKey,
      theme: ThemeData(primarySwatch: Colors.green),
      home: MainLayout(),
    );
  }
}
