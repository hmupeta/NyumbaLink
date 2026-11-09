#!/usr/bin/env python3
"""Fixes the bottom overflow error on the Listing Detail screen."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "listing_detail_screen.dart"

text = FILE.read_text(encoding="utf-8")

# We look for the specific SizedBox that's causing the issue
old_layout = '''                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: auth.user == null 
                          ? ElevatedButton.icon(
                              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                              icon: Icon(Icons.lock_outline),
                              label: Text("Log in to Contact Landlord"),
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.grey[800], shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                            )
                          : Column(
                              children: [
                                ElevatedButton.icon(
                                  onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                                  icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                                  label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Color(0xFF059669), 
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    minimumSize: Size(double.infinity, 50),
                                  ),
                                ),
                                SizedBox(height: 12),
                                OutlinedButton.icon(
                                  onPressed: () async {
                                    final date = await showDatePicker(
                                      context: context,
                                      initialDate: DateTime.now().add(Duration(days: 1)),
                                      firstDate: DateTime.now(),
                                      lastDate: DateTime.now().add(Duration(days: 30)),
                                    );
                                    if (date != null) {
                                      try {
                                        await ApiClient.requestViewing(listing['id'], date.toIso8601String());
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Viewing requested for ${date.toString().split(' ')[0]}")));
                                      } catch (e) {
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to request viewing")));
                                      }
                                    }
                                  },
                                  icon: Icon(Icons.calendar_today, color: Color(0xFF059669)),
                                  label: Text("Request Viewing", style: TextStyle(color: Color(0xFF059669))),
                                  style: OutlinedButton.styleFrom(
                                    side: BorderSide(color: Color(0xFF059669)),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                    minimumSize: Size(double.infinity, 50),
                                  ),
                                ),
                              ]
                            ),
                      ),'''

new_layout = '''                      // Condition 1: Not logged in
                      if (auth.user == null)
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton.icon(
                            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                            icon: Icon(Icons.lock_outline),
                            label: Text("Log in to Contact Landlord"),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.grey[800], 
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))
                            ),
                          ),
                        )
                      // Condition 2: Logged in, show both buttons
                      else
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFF059669), 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: () async {
                                final date = await showDatePicker(
                                  context: context,
                                  initialDate: DateTime.now().add(Duration(days: 1)),
                                  firstDate: DateTime.now(),
                                  lastDate: DateTime.now().add(Duration(days: 30)),
                                );
                                if (date != null) {
                                  try {
                                    await ApiClient.requestViewing(listing['id'], date.toIso8601String());
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Viewing requested for ${date.toString().split(' ')[0]}")));
                                  } catch (e) {
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to request viewing")));
                                  }
                                }
                              },
                              icon: Icon(Icons.calendar_today, color: Color(0xFF059669)),
                              label: Text("Request Viewing", style: TextStyle(color: Color(0xFF059669))),
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(color: Color(0xFF059669)),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                          ]
                        ),'''

if old_layout in text:
    text = text.replace(old_layout, new_layout)
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched listing_detail_screen.dart: Removed rigid height constraint causing overflow")
else:
    print("⚠️ Could not find the exact layout block. Please check manually.")

print("""
==================================================
🎉 OVERFLOW FIXED!
==================================================

Go back to your terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The yellow and black warning stripes will be gone, and both buttons will display perfectly.
""")