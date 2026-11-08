#!/usr/bin/env python3
"""NyumbaLink Phase 27e: Fix Chat Flickering, Emojis, Attachments & Voice."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Update Pubspec
PUBSPEC = MOBILE / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")
if "file_picker" not in text:
    deps = """
  file_picker: ^6.1.1
  record: ^5.0.4
  path_provider: ^2.1.2
  path: ^1.9.0
"""
    text = text.replace("  shared_preferences: ^2.2.2\n", "  shared_preferences: ^2.2.2\n" + deps)
    PUBSPEC.write_text(text, encoding="utf-8")
    print("✅ Added file_picker and record to pubspec.yaml")
    subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)

# ---------------------------------------------------------------- 2. Update API Client
API_CLIENT = '''
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http_parser/http_parser.dart';

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

  static Future<void> sendFileMessage(String conversationId, String filePath, String fileName, String type) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/conversations/$conversationId/messages/'),
    );
    
    final token = await getToken();
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    
    request.fields['body'] = type == 'AUDIO' ? 'Voice Note' : 'Attachment';
    request.fields['message_type'] = type;
    
    request.files.add(await http.MultipartFile.fromPath(
      'file',
      filePath,
      filename: fileName,
      contentType: type == 'AUDIO' ? MediaType('audio', 'mp4') : null,
    ));

    final response = await request.send();
    if (response.statusCode != 201) throw Exception('Failed to send file');
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

# ---------------------------------------------------------------- 3. Update Chat Screen
CHAT_SCREEN = '''
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
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
  List<dynamic> _messages = [];
  bool _isLoading = true;
  final _msgCtrl = TextEditingController();
  bool _sending = false;
  Timer? _pollingTimer;
  final _audioRecorder = AudioRecorder();
  bool _isRecording = false;

  @override
  void initState() {
    super.initState();
    _loadMessages();
    // Polling every 4 seconds for new messages / read receipts
    _pollingTimer = Timer.periodic(Duration(seconds: 4), (timer) => _loadMessages(silent: true));
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _audioRecorder.dispose();
    _msgCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadMessages({bool silent = false}) async {
    if (!silent) setState(() => _isLoading = true);
    try {
      final msgs = await ApiClient.getMessages(widget.conversationId);
      if (mounted) {
        setState(() {
          _messages = msgs;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _sendText() async {
    if (_msgCtrl.text.trim().isEmpty) return;
    setState(() => _sending = true);
    try {
      await ApiClient.sendMessage(widget.conversationId, _msgCtrl.text);
      _msgCtrl.clear();
      await _loadMessages(silent: true);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to send")));
    }
    setState(() => _sending = false);
  }

  void _pickFile() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles();
    if (result != null) {
      setState(() => _sending = true);
      try {
        await ApiClient.sendFileMessage(
          widget.conversationId,
          result.files.single.path!,
          result.files.single.name,
          'FILE',
        );
        await _loadMessages(silent: true);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to upload file")));
      }
      setState(() => _sending = false);
    }
  }

  void _toggleRecording() async {
    if (_isRecording) {
      final path = await _audioRecorder.stop();
      setState(() => _isRecording = false);
      if (path != null) {
        setState(() => _sending = true);
        try {
          await ApiClient.sendFileMessage(widget.conversationId, path, 'audio.m4a', 'AUDIO');
          await _loadMessages(silent: true);
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to send voice note")));
        }
        setState(() => _sending = false);
      }
    } else {
      if (await _audioRecorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = p.join(dir.path, 'recording.m4a');
        await _audioRecorder.start(const RecordConfig(), path: path);
        setState(() => _isRecording = true);
      }
    }
  }

  void _showReactionMenu(String messageId) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          padding: EdgeInsets.all(16),
          margin: EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(30)),
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
            child: _isLoading
              ? Center(child: CircularProgressIndicator())
              : ListView.builder(
                  padding: EdgeInsets.all(16),
                  itemCount: _messages.length,
                  itemBuilder: (context, index) {
                    final m = _messages[index];
                    final isMine = m['sender'] == myId;
                    final reactions = m['reactions'] as List<dynamic>? ?? [];
                    final msgType = m['message_type'] ?? 'TEXT';

                    return GestureDetector(
                      onLongPress: () => _showReactionMenu(m['id']),
                      child: Align(
                        alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
                        child: Column(
                          crossAxisAlignment: isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin: EdgeInsets.only(bottom: 4),
                              padding: EdgeInsets.all(12),
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
                                  if (msgType == 'TEXT')
                                    Text(m['body'] ?? '', style: TextStyle(color: isMine ? Colors.white : Colors.black87, fontSize: 16))
                                  else if (msgType == 'AUDIO')
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.play_arrow, color: isMine ? Colors.white : Colors.black87),
                                        SizedBox(width: 4),
                                        Text("Voice Note", style: TextStyle(color: isMine ? Colors.white : Colors.black87)),
                                      ],
                                    )
                                  else
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.attach_file, color: isMine ? Colors.white : Colors.black87),
                                        SizedBox(width: 4),
                                        Text("Attachment", style: TextStyle(color: isMine ? Colors.white : Colors.black87)),
                                      ],
                                    ),
                                  SizedBox(height: 4),
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (isMine)
                                        Icon(
                                          m['is_read'] ? Icons.done_all : Icons.check,
                                          size: 14,
                                          color: m['is_read'] ? Colors.lightBlueAccent : Colors.white70,
                                        ),
                                    ],
                                  )
                                ],
                              ),
                            ),
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
                ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            color: Colors.white,
            child: Row(
              children: [
                IconButton(
                  icon: Icon(Icons.attach_file, color: Colors.grey[600]),
                  onPressed: _sending ? null : _pickFile,
                ),
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
                  icon: Icon(_isRecording ? Icons.stop : Icons.mic, color: _isRecording ? Colors.red : Color(0xFF059669)),
                  onPressed: _sending ? null : _toggleRecording,
                ),
                IconButton(
                  icon: Icon(Icons.send, color: Color(0xFF059669)),
                  onPressed: _sending ? null : _sendText,
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
🎉 PHASE 27e COMPLETE: CHAT PERFECTED
==================================================

1. **No More Flickering**: The chat now loads messages into a local list instead of rebuilding the whole UI. The polling runs silently every 4 seconds.
2. **Emoji Reactions**: Long-press any message. When you tap an emoji, it instantly updates on the screen.
3. **Attachments**: Click the paperclip icon to pick a file/image.
4. **Voice Recorder**: Click the microphone to start recording. Click it again (it turns red) to stop and send.

**How to run:**
Since we added new native plugins (`record` and `file_picker`), you MUST fully stop and restart the app (press 'q', then run again).

Run: flutter run -d chrome --web-port 5173
""")