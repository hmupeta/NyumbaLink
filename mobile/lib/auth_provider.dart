import 'package:flutter/material.dart';
import 'api_client.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String email, String password) async {
    _user = await ApiClient.login(email, password);
    notifyListeners();
  }
}
