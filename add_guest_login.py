#!/usr/bin/env python3
"""Adds a 'Continue as Guest' link to the Flutter Login screen."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "login_screen.dart"

text = FILE.read_text(encoding="utf-8")

# Check if MainLayout is imported (it should be from the previous fix)
if "import 'main_layout.dart';" not in text:
    text = text.replace(
        "import 'auth_provider.dart';",
        "import 'auth_provider.dart';\nimport 'main_layout.dart';"
    )

# Find the Login button block and add the Guest button below it
old_button = '''              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                  child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Login"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}'''

new_button = '''              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                  child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Login"),
                ),
              ),
              SizedBox(height: 16),
              TextButton(
                onPressed: () {
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (_) => MainLayout()),
                  );
                },
                child: Text(
                  "Continue Browsing as Guest",
                  style: TextStyle(color: Colors.grey[700], fontSize: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}'''

if old_button in text:
    text = text.replace(old_button, new_button)
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched login_screen.dart: Added 'Continue Browsing as Guest' button")
else:
    print("⚠️ Could not find the exact login button block. Please check manually.")

print("""
==================================================
🎉 GUEST ACCESS ADDED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.

Now, on the Login screen, you will see a "Continue Browsing as Guest" link
below the Login button. Clicking it will take you straight to the Home feed!
""")