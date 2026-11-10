#!/usr/bin/env python3
"""Adds a 'Submit for Review' button to the mobile Manage Property screen."""
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "submitListing" not in text:
    text = text.replace(
        "  static Future<void> updateListing(String id, Map<String, dynamic> data) async {",
        '''  static Future<void> submitListing(String id) async {
    final res = await http.post(
      Uri.parse('$baseUrl/listings/$id/submit/'),
      headers: await getHeaders(),
    );
    if (res.statusCode != 200) throw Exception('Failed to submit listing');
  }

  static Future<void> updateListing(String id, Map<String, dynamic> data) async {'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added submitListing method")

# ----------------------------------------------------------------
# 2. Update Manage Listing Screen
# ----------------------------------------------------------------
MANAGE_FILE = LIB / "manage_listing_screen.dart"
text = MANAGE_FILE.read_text(encoding="utf-8")

# 2a. Add a submit method
if "_submitForReview" not in text:
    text = text.replace(
        "  void _saveChanges() async {",
        '''  void _submitForReview() async {
    setState(() => _isLoading = true);
    try {
      await ApiClient.submitListing(widget.listingId);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Listing submitted for review!")));
      widget.onUpdate(); // Refresh the dashboard
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit listing")));
      setState(() => _isLoading = false);
    }
  }

  void _saveChanges() async {'''
    )

# 2b. Add the button to the UI
    old_actions = '''                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _saveChanges,
                        style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                        child: Text("Save Changes"),
                      ),
                    ),'''

    new_actions = '''                    // Submit for Review button (only if DRAFT)
                    if (status == 'DRAFT') ...[
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: _submitForReview,
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700]),
                          child: Text("Submit for Review"),
                        ),
                      ),
                      SizedBox(height: 12),
                    ],

                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _saveChanges,
                        style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                        child: Text("Save Changes"),
                      ),
                    ),'''
    
    text = text.replace(old_actions, new_actions)
    MANAGE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched manage_listing_screen.dart: Added Submit for Review button")
else:
    print("⚠️ Could not find exact layout block in manage_listing_screen.dart.")

print("""
==================================================
🎉 DRAFT SUBMISSION ADDED!
==================================================

Go back to your terminal, quit ('q'), and restart the app.

1. Open the "2 Bed-roomed Modern Flats" property in your dashboard.
2. You will now see a blue **"Submit for Review"** button above "Save Changes".
3. Click it. The listing will change from DRAFT to SUBMITTED.
4. Now go to the Web Moderation Console, and you will see it waiting there for approval!
""")