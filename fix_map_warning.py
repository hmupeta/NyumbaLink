#!/usr/bin/env python3
"""Installs and configures the cancellable tile provider for flutter_map."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Add to pubspec.yaml
# ----------------------------------------------------------------
print("📦 Installing flutter_map_cancellable_tile_provider...")
PUBSPEC = MOBILE / "pubspec.yaml"
text = PUBSPEC.read_text(encoding="utf-8")

if "flutter_map_cancellable_tile_provider" not in text:
    text = text.replace(
        "  flutter_map: ^6.1.0",
        "  flutter_map: ^6.1.0\n  flutter_map_cancellable_tile_provider: ^2.0.0"
    )
    PUBSPEC.write_text(text, encoding="utf-8")
    subprocess.run(["flutter", "pub", "get"], cwd=MOBILE, shell=True)
    print("✅ Added dependency")

# ----------------------------------------------------------------
# 2. Update MapView to use it
# ----------------------------------------------------------------
MAP_FILE = LIB / "map_view.dart"
text = MAP_FILE.read_text(encoding="utf-8")

if "CancellableNetworkTileProvider" not in text:
    text = text.replace(
        "import 'package:flutter_map/flutter_map.dart';",
        "import 'package:flutter_map/flutter_map.dart';\nimport 'package:flutter_map_cancellable_tile_provider/flutter_map_cancellable_tile_provider.dart';"
    )
    
    text = text.replace(
        '''            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.nyumbalink.mobile',
            ),''',
        '''            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.nyumbalink.mobile',
              tileProvider: CancellableNetworkTileProvider(),
            ),'''
    )
    MAP_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched map_view.dart: Using CancellableNetworkTileProvider")

print("""
==================================================
🎉 MAP WARNING FIXED!
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app:
  flutter run -d chrome

The warning will be gone, and your map will now load and pan much faster!
""")