#!/usr/bin/env python3
"""Rewrites pubspec.yaml with correct structure and assets."""
from pathlib import Path
import subprocess

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
PUBSPEC = MOBILE / "pubspec.yaml"

PUBSPEC_CONTENT = '''name: mobile
description: "A new Flutter project."
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  http: ^1.1.0
  provider: ^6.1.1
  shared_preferences: ^2.2.2
  cached_network_image: ^3.3.0
  intl: ^0.18.1
  http_parser: ^4.0.2
  file_picker: ^6.1.1
  record: ^5.0.4
  path_provider: ^2.1.2
  path: ^1.9.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  flutter_launcher_icons: ^0.13.1

flutter_launcher_icons:
  android: true
  ios: true
  image_path: "assets/images/logo.png"

flutter:
  uses-material-design: true
  assets:
    - assets/images/
'''

PUBSPEC.write_text(PUBSPEC_CONTENT, encoding="utf-8")
print("✅ Rewrote pubspec.yaml with correct structure")

print("\n⏳ Running flutter pub get...")
subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)

print("\n⏳ Generating launcher icons...")
subprocess.run(["dart", "run", "flutter_launcher_icons"], cwd=MOBILE, shell=True)

print("""
==================================================
🎉 PUPSPEC FIXED AND ICONS GENERATED!
==================================================

Now go back to Flutter and restart the app:
  q
  flutter run -d chrome

The app icon and in-app logo should now be visible!
""")