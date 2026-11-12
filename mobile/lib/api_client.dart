import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http_parser/http_parser.dart';

import 'package:flutter/material.dart';

class ApiClient {
  static VoidCallback? onUnauthorized;
  static const String baseUrl = "https://nyumbalink-backend-eaw2.onrender.com/api/v1";
  
  static void _checkResponse(int statusCode) {
    if (statusCode == 401) {
      onUnauthorized?.call();
      throw Exception('Session expired');
    }
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  static Future<void> setToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  static Future<Map<String, String>> getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static Future<List<dynamic>> getListings({
    String? query, 
    String? transactionType, 
    String? propertyType, 
    int? minBedrooms, 
    double? maxPrice
  }) async {
    final params = <String, String>{};
    if (query != null && query.isNotEmpty) params['search'] = query;
    if (transactionType != null && transactionType.isNotEmpty) params['transaction_type'] = transactionType;
    if (propertyType != null && propertyType.isNotEmpty) params['property_type'] = propertyType;
    if (minBedrooms != null) params['min_bedrooms'] = minBedrooms.toString();
    if (maxPrice != null) params['max_price'] = maxPrice.toString();

    final uri = Uri.parse('$baseUrl/listings/').replace(queryParameters: params);
    final res = await http.get(uri, headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load listings');
  }

  static Future<Map<String, dynamic>> createNeighbourhood(String name) async {
    final res = await http.post(
      Uri.parse('$baseUrl/neighbourhoods/'),
      headers: await getHeaders(),
      body: jsonEncode({'name': name}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 200 || res.statusCode == 201) {
      return jsonDecode(res.body);
    }
    throw Exception('Failed to create neighbourhood');
  }

  static Future<Map<String, dynamic>> getListingDetail(String id) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/listings/$id/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body);
      throw Exception('Server returned ${res.statusCode}: ${res.body}');
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      await setToken(data['access']);
      return data['user'];
    }
    throw Exception('Invalid credentials');
  }

  static Future<Map<String, dynamic>> register(String email, String password, String firstName) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/register/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password, 'first_name': firstName}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 201) {
      final data = jsonDecode(res.body);
      await setToken(data['access']);
      return data['user'];
    }
    throw Exception('Registration failed');
  }

  // --- Landlord Features ---
  static Future<List<dynamic>> getMyListings() async {
    final res = await http.get(Uri.parse('$baseUrl/listings/my_listings/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load your listings');
  }

  static Future<List<dynamic>> getNeighbourhoods() async {
    final res = await http.get(Uri.parse('$baseUrl/neighbourhoods/?page=1'));
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load locations');
  }

  static Future<void> createPropertyAndListing({
    required String title,
    required String description,
    required double price,
    required int bedrooms,
    required int bathrooms,
    required double floorArea,
    required String propertyType,
    required String neighbourhoodId,
    required List<int> imageBytes,
    required String imageName,
  }) async {
    // 1. Create Property
    final propRes = await http.post(
      Uri.parse('$baseUrl/properties/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'neighbourhood': neighbourhoodId,
        'property_type': propertyType,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'floor_area': floorArea,
        'description': description,
      }),
    );
    if (propRes.statusCode != 201) throw Exception('Failed to create property');
    final propId = jsonDecode(propRes.body)['id'];

    // 2. Create Listing
    final listRes = await http.post(
      Uri.parse('$baseUrl/listings/'),
      headers: await getHeaders(),
      body: jsonEncode({
        'property': propId,
        'transaction_type': 'RENT',
        'price': price,
        'currency': 'ZMW',
        'title': title,
        'description': description,
      }),
    );
    if (listRes.statusCode != 201) throw Exception('Failed to create listing');
    final listingId = jsonDecode(listRes.body)['id'];

    // 3. Upload Image
    if (imageBytes.isNotEmpty) {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/listings/$listingId/media/'),
      );
      final token = await getToken();
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      
      request.files.add(http.MultipartFile.fromBytes('file', imageBytes, filename: imageName));
      request.fields['media_type'] = 'IMAGE';
      
      final mediaRes = await request.send();
      if (mediaRes.statusCode != 201) throw Exception('Listing created, but image upload failed');
    }
  }

  static Future<void> submitListing(String id) async {
    final res = await http.post(
      Uri.parse('$baseUrl/listings/$id/submit/'),
      headers: await getHeaders(),
    );
    if (res.statusCode != 200) throw Exception('Failed to submit listing');
  }

  static Future<void> updateListing(String id, Map<String, dynamic> data) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/listings/$id/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to update listing');
  }

  static Future<void> deleteListing(String id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/listings/$id/'),
      headers: await getHeaders(),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 204) throw Exception('Failed to delete listing');
  }


  // --- Notifications ---
  static Future<int> getUnreadNotificationCount() async {
    final res = await http.get(Uri.parse('$baseUrl/notifications/unread_count/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['count'];
    return 0;
  }

  static Future<List<dynamic>> getNotifications() async {
    final res = await http.get(Uri.parse('$baseUrl/notifications/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load notifications');
  }

  static Future<void> markAllNotificationsRead() async {
    await http.post(Uri.parse('$baseUrl/notifications/mark_all_read/'), headers: await getHeaders());
  }

  // --- Viewing Requests ---
  static Future<void> requestViewing(String listingId, String dateIso) async {
    final res = await http.post(
      Uri.parse('$baseUrl/viewings/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing': listingId, 'requested_date': dateIso, 'note': 'Requested via mobile app'}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 201) throw Exception('Failed to request viewing');
  }

  static Future<List<dynamic>> getViewingRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/viewings/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      return data['results'] ?? [];
    }
    throw Exception('Failed to load viewing requests');
  }

  static Future<void> updateViewingStatus(String viewingId, String status) async {
    final res = await http.post(
      Uri.parse('$baseUrl/viewings/$viewingId/update_status/'),
      headers: await getHeaders(),
      body: jsonEncode({'status': status}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to update status');
  }



  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    
    // Safety: If the server returns HTML (like a 500 error page), don't crash trying to parse it as JSON
    try {
      final decoded = jsonDecode(res.body);
      if (res.statusCode >= 200 && res.statusCode < 300) {
        return decoded;
      }
      final error = decoded['detail'] ?? 'Request failed';
      throw Exception(error);
    } catch (e) {
      if (e is FormatException) {
        throw Exception("Server error (${res.statusCode}). Please try again later.");
      }
      rethrow;
    }
  }

  // --- Direct Payments ---
  static Future<void> unlockListing(String listingId, String provider, String phone) async {
    final res = await http.post(
      Uri.parse('$baseUrl/unlock/unlock/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId, 'provider': provider, 'phone_number': phone}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) {
      final error = jsonDecode(res.body)['detail'] ?? 'Failed to unlock';
      throw Exception(error);
    }
  }


  static Future<void> payRent(String listingId, double amount, String type, String phone) async {
    final res = await http.post(
      Uri.parse('$baseUrl/rent/pay_rent/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId, 'amount': amount, 'type': type, 'phone_number': phone}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) {
      final error = jsonDecode(res.body)['detail'] ?? 'Payment failed';
      throw Exception(error);
    }
  }

  static Future<Map<String, dynamic>> getPaymentSettings() async {
    final res = await http.get(Uri.parse('$baseUrl/payment-settings/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load settings');
  }

  static Future<void> updatePaymentSettings(Map<String, dynamic> data) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/payment-settings/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to update settings');
  }


  // --- KYC / Verification ---
  static Future<List<dynamic>> getVerificationCases() async {
    final res = await http.get(Uri.parse('$baseUrl/verifications/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load verifications');
  }

  static Future<Map<String, dynamic>> createVerificationCase(String type) async {
    final res = await http.post(
      Uri.parse('$baseUrl/verifications/'),
      headers: await getHeaders(),
      body: jsonEncode({'verification_type': type}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 201) return jsonDecode(res.body);
    throw Exception('Failed to create verification case');
  }

  static Future<void> uploadVerificationDocument(String caseId, List<int> fileBytes, String fileName, String docType) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/verifications/$caseId/documents/'),
    );
    final token = await getToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    
    request.fields['document_type'] = docType;
    request.files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: fileName));
    
    final response = await request.send();
    _checkResponse(response.statusCode);
    if (response.statusCode != 201) throw Exception('Failed to upload document');
  }


  // --- Profiles & Reviews ---
  static Future<Map<String, dynamic>> getPublicProfile(String userId) async {
    final res = await http.get(Uri.parse('$baseUrl/profiles/$userId/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load profile');
  }

  static Future<void> submitReview(String userId, int rating, String comment) async {
    final res = await http.post(
      Uri.parse('$baseUrl/profiles/$userId/reviews/'),
      headers: await getHeaders(),
      body: jsonEncode({'rating': rating, 'comment': comment}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 201) {
      final error = jsonDecode(res.body);
      throw Exception(error.values.first[0] ?? 'Failed to submit review');
    }
  }


  // --- Management (Tenants & Leases) ---
  static Future<List<dynamic>> getLeases() async {
    final res = await http.get(Uri.parse('$baseUrl/leases/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load leases');
  }

  static Future<void> markRentPaid(String leaseId, String recordId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/leases/$leaseId/rent-records/$recordId/mark_paid/'),
      headers: await getHeaders(),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to mark rent paid');
  }

  static Future<List<dynamic>> getMyTenancy() async {
    final res = await http.get(Uri.parse('$baseUrl/leases/my_tenancy/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load tenancy');
  }

  static Future<void> createMaintenanceRequest(Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl/maintenance/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 201) throw Exception('Failed to log maintenance');
  }

  // --- Maintenance ---
  static Future<List<dynamic>> getMaintenanceRequests() async {
    final res = await http.get(Uri.parse('$baseUrl/maintenance/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load maintenance requests');
  }

  static Future<void> updateMaintenanceStatus(String id, String status) async {
    final res = await http.post(
      Uri.parse('$baseUrl/maintenance/$id/update_status/'),
      headers: await getHeaders(),
      body: jsonEncode({'status': status}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to update maintenance status');
  }


  // --- Saved Searches ---
  static Future<List<dynamic>> getSavedSearches() async {
    final res = await http.get(Uri.parse('$baseUrl/saved-searches/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load saved searches');
  }

  static Future<void> createSavedSearch(Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl/saved-searches/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (res.statusCode != 201) throw Exception('Failed to save search');
  }

  static Future<void> deleteSavedSearch(String id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/saved-searches/$id/'),
      headers: await getHeaders(),
    );
    if (res.statusCode != 204) throw Exception('Failed to delete saved search');
  }


  // --- Lease Agreements ---
  static Future<Map<String, dynamic>> getLeaseDetails(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/leases/$id/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load lease');
  }

  static Future<Map<String, dynamic>> generateLeaseAgreement(String id) async {
    final res = await http.post(Uri.parse('$baseUrl/leases/$id/generate_agreement/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to generate agreement');
  }

  static Future<Map<String, dynamic>> signLease(String id) async {
    final res = await http.post(Uri.parse('$baseUrl/leases/$id/sign/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to sign lease');
  }

  static Future<Map<String, dynamic>> requestLease(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/leases/request_lease/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    if (res.statusCode == 200 || res.statusCode == 201) return jsonDecode(res.body);
    throw Exception('Failed to request lease');
  }

  static Future<void> submitReport(String listingId, String reason, String description) async {
    final res = await http.post(
      Uri.parse('$baseUrl/reports/'),
      headers: await getHeaders(),
      body: jsonEncode({'target_listing': listingId, 'reason': reason, 'description': description}),
    );
    if (res.statusCode != 201) throw Exception('Failed to submit report');
  }

  static Future<void> requestPasswordReset(String email) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/password-reset/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'origin': 'https://nyumbalink-frontend-pbkm.onrender.com'}),
    );
    if (res.statusCode != 200) throw Exception('Failed to send reset link');
  }

  // --- Saved Properties ---
  static Future<List<dynamic>> getSavedListings() async {
    final res = await http.get(Uri.parse('$baseUrl/saved-listings/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load saved listings');
  }

  static Future<void> toggleSaveListing(String listingId, bool isSaved) async {
    if (isSaved) {
      await http.delete(Uri.parse('$baseUrl/saved-listings/$listingId/'), headers: await getHeaders());
    } else {
      await http.post(
        Uri.parse('$baseUrl/saved-listings/'),
        headers: await getHeaders(),
        body: jsonEncode({'listing_id': listingId}),
      );
    }
  }

  // --- Messaging ---
  static Future<List<dynamic>> getConversations() async {
    final res = await http.get(Uri.parse('$baseUrl/conversations/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load conversations');
  }

  static Future<String> startConversation(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/start/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['id'];
    throw Exception('Failed to start chat');
  }

  static Future<List<dynamic>> getMessages(String conversationId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load messages');
  }

  static Future<void> sendMessage(String conversationId, String body) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
      body: jsonEncode({'body': body}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 201) throw Exception('Failed to send message');
  }

  static Future<void> sendFileMessage(String conversationId, List<int> fileBytes, String fileName, String type) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
    );
    final token = await getToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    request.fields['body'] = type == 'AUDIO' ? 'Voice Note' : 'Attachment';
    request.fields['message_type'] = type;
    request.files.add(http.MultipartFile.fromBytes(
      'file', fileBytes, filename: fileName,
      contentType: type == 'AUDIO' ? MediaType('audio', 'mp4') : null,
    ));
    final response = await request.send();
    _checkResponse(response.statusCode);
    if (response.statusCode != 201) throw Exception('Failed to send file');
  }

  static Future<void> reactToMessage(String conversationId, String messageId, String emoji) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/$messageId/react/'),
      headers: await getHeaders(),
      body: jsonEncode({'emoji': emoji}),
    );
    _checkResponse(res.statusCode);
    if (res.statusCode != 200) throw Exception('Failed to react');
  }

  static Future<Map<String, dynamic>> checkStatus(String reference) async {
    final res = await http.get(Uri.parse('$baseUrl/payments/status/$reference/'), headers: await getHeaders());
    _checkResponse(res.statusCode);
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to check payment status');
  }
}
