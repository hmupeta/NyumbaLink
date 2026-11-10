#!/usr/bin/env python3
"""NyumbaLink Phase 39: Mobile KYC & Verification."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getVerificationCases" not in text:
    new_methods = '''
  // --- KYC / Verification ---
  static Future<List<dynamic>> getVerificationCases() async {
    final res = await http.get(Uri.parse('$baseUrl/verifications/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body)['results'];
    throw Exception('Failed to load verifications');
  }

  static Future<Map<String, dynamic>> createVerificationCase(String type) async {
    final res = await http.post(
      Uri.parse('$baseUrl/verifications/'),
      headers: await getHeaders(),
      body: jsonEncode({'verification_type': type}),
    );
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
    if (response.statusCode != 201) throw Exception('Failed to upload document');
  }

  // --- Saved Properties ---'''
    
    text = text.replace("  // --- Saved Properties ---", new_methods)
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added KYC methods")

# ----------------------------------------------------------------
# 2. Flutter: Create Verification Screen
# ----------------------------------------------------------------
VERIFICATION_SCREEN = '''
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'api_client.dart';

class VerificationScreen extends StatefulWidget {
  @override
  _VerificationScreenState createState() => _VerificationScreenState();
}

class _VerificationScreenState extends State<VerificationScreen> {
  bool _isLoading = true;
  List<dynamic> _cases = [];
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    try {
      final cases = await ApiClient.getVerificationCases();
      if (mounted) setState(() { _cases = cases; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _startCase(String type) async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.createVerificationCase(type);
      await _loadCases();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  Future<void> _uploadDoc(String caseId) async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
    if (result != null) {
      setState(() => _isProcessing = true);
      try {
        await ApiClient.uploadVerificationDocument(
          caseId, 
          result.files.single.bytes!, 
          result.files.single.name, 
          'Document'
        );
        await _loadCases();
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Document uploaded!")));
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Upload failed")));
      }
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Widget _buildCaseCard(String title, String description, String type) {
    final existingCase = _cases.firstWhere(
      (c) => c['verification_type'] == type, 
      orElse: () => null
    );

    final status = existingCase?['status'];
    final docs = existingCase?['documents'] as List<dynamic>? ?? [];

    return Card(
      margin: EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                if (status != null)
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: status == 'APPROVED' ? Colors.green[100] : status == 'REJECTED' ? Colors.red[100] : Colors.orange[100],
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(status, style: TextStyle(
                      fontSize: 10, 
                      fontWeight: FontWeight.bold,
                      color: status == 'APPROVED' ? Colors.green[800] : status == 'REJECTED' ? Colors.red[800] : Colors.orange[800]
                    )),
                  )
              ],
            ),
            SizedBox(height: 8),
            Text(description, style: TextStyle(color: Colors.grey[600], fontSize: 14)),
            SizedBox(height: 16),
            if (existingCase == null)
              ElevatedButton(
                onPressed: _isProcessing ? null : () => _startCase(type),
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: Text("Start Verification"),
              )
            else if (status == 'REJECTED')
              Text("Rejected: ${existingCase['rejection_reason']}", style: TextStyle(color: Colors.red))
            else if (status == 'PENDING' || status == 'APPROVED')
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Uploaded Documents:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  SizedBox(height: 8),
                  ...docs.map((d) => Text("• ${d['document_type']} (Uploaded)", style: TextStyle(color: Colors.green[700]))),
                  SizedBox(height: 12),
                  if (status != 'APPROVED')
                    OutlinedButton.icon(
                      onPressed: _isProcessing ? null : () => _uploadDoc(existingCase['id']),
                      icon: Icon(Icons.upload_file),
                      label: Text("Upload Document"),
                    )
                ],
              )
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Verification Center"), backgroundColor: Color(0xFF059669)),
      body: _isLoading 
        ? Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                Text("Build trust by verifying your identity and property ownership.", style: TextStyle(color: Colors.grey[600])),
                SizedBox(height: 24),
                _buildCaseCard(
                  "Identity Verification", 
                  "Upload your NRC or Passport to prove who you are.", 
                  "IDENTITY"
                ),
                _buildCaseCard(
                  "Ownership / Authority", 
                  "Upload Title Deeds or a Landlord authorization letter.", 
                  "OWNERSHIP_AUTHORITY"
                ),
              ],
            ),
          ),
    );
  }
}
'''
(LIB / "verification_screen.dart").write_text(VERIFICATION_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created verification_screen.dart")

# ----------------------------------------------------------------
# 3. Flutter: Link Verification in Profile
# ----------------------------------------------------------------
PROFILE_FILE = LIB / "profile_screen.dart"
text = PROFILE_FILE.read_text(encoding="utf-8")

if "VerificationScreen" not in text:
    text = text.replace(
        "import 'landlord_dashboard_screen.dart';",
        "import 'landlord_dashboard_screen.dart';\nimport 'verification_screen.dart';"
    )
    
    # Replace the old "Verification" stub
    old_stub = '''                ListTile(
                  leading: Icon(Icons.verified_user, color: Color(0xFF059669)),
                  title: Text("Verification"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Verification coming soon to mobile!")));
                  },
                ),'''
    
    new_link = '''                ListTile(
                  leading: Icon(Icons.verified_user, color: Color(0xFF059669)),
                  title: Text("Verification Center"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => VerificationScreen())),
                ),'''
    
    text = text.replace(old_stub, new_link)
    PROFILE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched profile_screen.dart: Linked Verification Screen")

print("""
==================================================
🎉 PHASE 39 COMPLETE: MOBILE KYC
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. Go to the Profile tab.
2. Click **Verification Center**.
3. Click **Start Verification** under Identity.
4. Click **Upload Document** and pick an image of your NRC.
5. The document will upload to your Cloudinary backend.
6. You can now log into the Web Admin (Moderation Console) and approve it!
""")