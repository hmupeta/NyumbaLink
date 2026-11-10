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
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Show rejection message if applicable
                  if (status == 'REJECTED')
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text("Rejected: ${existingCase['rejection_reason']}", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                    ),

                  if (docs.isNotEmpty) ...[
                    Text("Uploaded Documents:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    SizedBox(height: 8),
                    ...docs.map((d) => Text("• ${d['document_type']} (Uploaded)", style: TextStyle(color: Colors.green[700]))),
                    SizedBox(height: 12),
                  ],

                  // Allow upload if pending or rejected
                  if (status != 'APPROVED')
                    OutlinedButton.icon(
                      onPressed: _isProcessing ? null : () => _uploadDoc(existingCase['id']),
                      icon: Icon(Icons.upload_file),
                      label: Text(status == 'REJECTED' ? "Re-upload Document" : "Upload Document"),
                      style: OutlinedButton.styleFrom(side: BorderSide(color: Color(0xFF059669)), foregroundColor: Color(0xFF059669)),
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
