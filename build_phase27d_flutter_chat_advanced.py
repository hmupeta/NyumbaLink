#!/usr/bin/env python3
"""NyumbaLink Phase 27d: Flutter Advanced Chat (Ticks, Reactions, Alignment)."""
from __future__ import annotations
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Update API Client
API_CLIENT = '''
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String baseUrl = "https://nyumbalink-backend-eaw2.onrender.com/api/v1";
  
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

  static Future<List<dynamic>> getListings({String? query}) async {
    String url = '$baseUrl/listings/';
    if (query != null && query.isNotEmpty) url += '?search=$query';
    final res = await http.get(Uri.parse(url), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load listings');
  }

  static Future<Map<String, dynamic>> getListingDetail(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/listings/$id/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load listing');
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
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
    if (res.statusCode == 201) {
      final data = jsonDecode(res.body);
      await setToken(data['access']);
      return data['user'];
    }
    throw Exception('Registration failed');
  }

  // --- Messaging ---
  static Future<String> startConversation(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/start/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    if (res.statusCode == 200) return jsonDecode(res.body)['id'];
    throw Exception('Failed to start chat');
  }

  static Future<List<dynamic>> getMessages(String conversationId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
    );
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load messages');
  }

  static Future<void> sendMessage(String conversationId, String body) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
      headers: await getHeaders(),
      body: jsonEncode({'body': body}),
    );
    if (res.statusCode != 201) throw Exception('Failed to send message');
  }

  static Future<void> reactToMessage(String conversationId, String messageId, String emoji) async {
    final res = await http.post(
      Uri.parse('$baseUrl/conversations/$conversationId/messages/$messageId/react/'),
      headers: await getHeaders(),
      body: jsonEncode({'emoji': emoji}),
    );
    if (res.statusCode != 200) throw Exception('Failed to react');
  }
}
'''
(LIB / "api_client.dart").write_text(API_CLIENT.strip() + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 2. Update Chat Screen
CHAT_SCREEN = '''
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';

class ChatScreen extends StatefulWidget {
  final String conversationId;
  final String landlordName;

  ChatScreen({required this.conversationId, required this.landlordName});

  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late Future<List<dynamic>> _messagesFuture;
  final _msgCtrl = TextEditingController();
  bool _sending = false;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _loadMessages();
    // Poll every 5 seconds to update read receipts and get new messages
    _pollingTimer = Timer.periodic(Duration(seconds: 5), (timer) {
      if (mounted) _loadMessages(silent: true);
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _msgCtrl.dispose();
    super.dispose();
  }

  void _loadMessages({bool silent = false}) {
    if (!silent) {
      setState(() { _messagesFuture = ApiClient.getMessages(widget.conversationId); });
    } else {
      setState(() { _messagesFuture = ApiClient.getMessages(widget.conversationId); });
    }
  }

  void _send() async {
    if (_msgCtrl.text.trim().isEmpty) return;
    setState(() => _sending = true);
    try {
      await ApiClient.sendMessage(widget.conversationId, _msgCtrl.text);
      _msgCtrl.clear();
      _loadMessages();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to send")));
    }
    setState(() => _sending = false);
  }

  void _showReactionMenu(String messageId) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: EdgeInsets.all(16),
          margin: EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(30),
            boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 10)],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: ['👍', '❤️', '😂', '😮', '😢', '🙏'].map((emoji) {
              return GestureDetector(
                onTap: () async {
                  Navigator.pop(context);
                  await ApiClient.reactToMessage(widget.conversationId, messageId, emoji);
                  _loadMessages(silent: true);
                },
                child: Text(emoji, style: TextStyle(fontSize: 32)),
              );
            }).toList(),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final myId = auth.user?['id'];

    return Scaffold(
      appBar: AppBar(title: Text(widget.landlordName), backgroundColor: Color(0xFF059669)),
      body: Column(
        children: [
          Expanded(
            child: FutureBuilder<List<dynamic>>(
              future: _messagesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
                if (snapshot.hasError) return Center(child: Text("Error loading messages"));
                
                final msgs = snapshot.data!;
                return ListView.builder(
                  padding: EdgeInsets.all(16),
                  itemCount: msgs.length,
                  itemBuilder: (context, index) {
                    final m = msgs[index];
                    final isMine = m['sender'] == myId;
                    final reactions = m['reactions'] as List<dynamic>? ?? [];

                    return GestureDetector(
                      onLongPress: () => _showReactionMenu(m['id']),
                      child: Align(
                        alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
                        child: Column(
                          crossAxisAlignment: isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin: EdgeInsets.only(bottom: 4),
                              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              decoration: BoxDecoration(
                                color: isMine ? Color(0xFF059669) : Colors.grey[200],
                                borderRadius: BorderRadius.only(
                                  topLeft: Radius.circular(16),
                                  topRight: Radius.circular(16),
                                  bottomLeft: isMine ? Radius.circular(16) : Radius.circular(0),
                                  bottomRight: isMine ? Radius.circular(0) : Radius.circular(16),
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    m['body'] ?? '',
                                    style: TextStyle(color: isMine ? Colors.white : Colors.black87, fontSize: 16),
                                  ),
                                  SizedBox(height: 4),
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        "", // Time text could go here
                                        style: TextStyle(color: isMine ? Colors.white70 : Colors.black45, fontSize: 10),
                                      ),
                                      if (isMine) ...[
                                        SizedBox(width: 4),
                                        Icon(
                                          m['is_read'] ? Icons.done_all : Icons.check,
                                          size: 14,
                                          color: m['is_read'] ? Colors.lightBlueAccent : Colors.white70,
                                        ),
                                      ]
                                    ],
                                  )
                                ],
                              ),
                            ),
                            // Reactions
                            if (reactions.isNotEmpty)
                              Container(
                                margin: EdgeInsets.only(bottom: 8),
                                padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: Colors.grey[300]!),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: reactions.map((r) => Text(r['emoji'], style: TextStyle(fontSize: 12))).toList(),
                                ),
                              )
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _msgCtrl,
                    decoration: InputDecoration(
                      hintText: "Type a message...",
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                      contentPadding: EdgeInsets.symmetric(horizontal: 16),
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send, color: Color(0xFF059669)),
                  onPressed: _sending ? null : _send,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
'''
(LIB / "chat_screen.dart").write_text(CHAT_SCREEN.strip() + "\n", encoding="utf-8")

print("""
==================================================
🎉 PHASE 27d COMPLETE: WHATSAPP-STYLE CHAT!
==================================================

You MUST fully restart Flutter for the Timer and UI changes to work.
(Quit with 'q', then run again).

Here is what is new:
1. **Right Alignment**: Your messages are on the right (green), landlord's on the left (grey).
2. **Read Receipts**: When you send a message, it has a single tick (✓). When the other person opens the chat, it automatically updates to a blue double tick (✓✓) within 5 seconds.
3. **Emoji Reactions**: Long-press any message (yours or the landlord's) to bring up the emoji menu. Tap an emoji to attach it to the message.

To test the double ticks:
1. Send a message from the seeker account.
2. Open a second browser window, log in as landlord@nyumbalink.com.
3. Go to the Inbox, open the conversation. (This triggers the "read" event).
4. Go back to the first browser window. Wait 5 seconds. The tick will turn blue!
""")