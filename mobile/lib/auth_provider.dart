import 'package:flutter/material.dart';
import 'api_client.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String email, String password) async {
    _user = await ApiClient.login(email, password);
    notifyListeners();
  }

  Future<void> register(String email, String password, String firstName) async {
    _user = await ApiClient.register(email, password, firstName);
    notifyListeners();
  }

  Future<void> logout() async {
    await ApiClient.clearToken();
    _user = null;
    notifyListeners();
  }
}
