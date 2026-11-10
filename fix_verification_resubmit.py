#!/usr/bin/env python3
"""Allows landlords to resubmit rejected verification documents."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Backend: Reset status to PENDING on new document upload
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "verification" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

old_create = '''    def perform_create(self, serializer):
        case_id = self.kwargs.get("case_pk")
        case = VerificationCase.objects.get(id=case_id, user=self.request.user)
        serializer.save(case=case)'''

new_create = '''    def perform_create(self, serializer):
        case_id = self.kwargs.get("case_pk")
        case = VerificationCase.objects.get(id=case_id, user=self.request.user)
        serializer.save(case=case)
        
        # If they were rejected and are uploading a new document, put them back in the queue
        if case.status == "REJECTED":
            case.status = "PENDING"
            case.rejection_reason = ""
            case.save()'''

if old_create in text:
    text = text.replace(old_create, new_create)
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched verification/views.py: Re-uploads reset status to PENDING")
else:
    print("⚠️ Could not find exact perform_create block in verification views.")

# ----------------------------------------------------------------
# 2. Frontend: Show upload button even if REJECTED
# ----------------------------------------------------------------
FLUTTER_FILE = MOBILE / "lib" / "verification_screen.dart"
text = FLUTTER_FILE.read_text(encoding="utf-8")

old_ui = '''            else if (status == 'REJECTED')
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
              )'''

new_ui = '''            else
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
              )'''

if old_ui in text:
    text = text.replace(old_ui, new_ui)
    FLUTTER_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched verification_screen.dart: Added re-upload UI for rejected cases")
else:
    print("⚠️ Could not find exact UI block in verification_screen.dart")

# ----------------------------------------------------------------
# 3. Push backend changes to GitHub (Render will redeploy)
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Allow re-uploading rejected verification documents"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 VERIFICATION RESUBMISSION ENABLED!
==================================================

1. **Backend**: Render is rebuilding. Once live, uploading a new document to a rejected case will automatically change the status back to `PENDING`.
2. **Frontend**: The UI now shows a red rejection message AND a **"Re-upload Document"** button.

Go back to your Flutter terminal and press 'r' to hot reload.

Go to the Verification Center, and you will now be able to upload a new document to fix the rejection!
""")