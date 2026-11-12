#!/usr/bin/env python3
"""
tsx_parser_check.py — find real TSX syntax errors with tree-sitter.
No Node.js required.

Usage:
    python tsx_parser_check.py
    python tsx_parser_check.py frontend/src/pages/TenantsList.tsx
"""
from __future__ import annotations
import subprocess
import sys
import unicodedata
from pathlib import Path

TARGET = Path(sys.argv[1] if len(sys.argv) > 1
              else "frontend/src/pages/TenantsList.tsx")

if not TARGET.exists():
    sys.exit(f"❌  not found: {TARGET}")

# ---------- ensure tree-sitter is available --------------------------------
try:
    from tree_sitter import Language, Parser
    import tree_sitter_typescript as ts_ts
except ImportError:
    print("Installing tree-sitter (one-time, ~2 MB)...", flush=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "tree-sitter", "tree-sitter-typescript",
    ])
    from tree_sitter import Language, Parser
    import tree_sitter_typescript as ts_ts

# ---------- build parser (works across tree-sitter versions) --------------
TSX = Language(ts_ts.language_tsx())
try:
    parser = Parser(TSX)              # tree-sitter >= 0.22
except TypeError:
    parser = Parser()                 # tree-sitter <= 0.21
    parser.set_language(TSX)

# ---------- read & parse --------------------------------------------------
raw = TARGET.read_bytes()
lines = raw.split(b"\n")
tree = parser.parse(raw)

# ---------- collect ERROR / MISSING nodes --------------------------------
errors = []
def walk(node):
    if node.type == "ERROR" or node.is_missing:
        errors.append(node)
    for c in node.children:
        walk(c)
walk(tree.root_node)

# ---------- smart-quote scan ---------------------------------------------
SUSPICIOUS = {"\u2018", "\u2019", "\u201c", "\u201d", "\u2013", "\u2014"}
smart = []
for i, ln in enumerate(lines, 1):
    for col, ch in enumerate(ln.decode("utf-8", "replace"), 1):
        if ch in SUSPICIOUS:
            smart.append((i, col, ch, unicodedata.name(ch, "?")))

# ---------- report -------------------------------------------------------
if not errors:
    print("✅  tree-sitter found no syntax errors.")
else:
    print(f"❌  {len(errors)} syntax error(s):")
    for err in errors:
        sr, sc = err.start_point
        er, ec = err.end_point
        print(f"\n   {err.type} at line {sr+1}:{sc+1} → {er+1}:{ec+1}")
        lo, hi = max(0, sr - 3), min(len(lines), sr + 4)
        for i in range(lo, hi):
            marker = ">>" if i == sr else "  "
            print(f"   {marker}{i+1:4} | "
                  f"{lines[i].decode('utf-8', 'replace')}")

if smart:
    print(f"\n⚠️   {len(smart)} smart/typographic quote(s) found — "
          "these DO break TSX:")
    for ln, col, ch, name in smart:
        print(f"   line {ln}:{col}  '{ch}' ({name})")
    print("   → replace with plain ASCII ' \" -")

if not errors and not smart:
    print(
        "\nℹ️   Syntactically clean. If `npx tsc` still errors, the issue "
        "is a *type* error, not syntax — install Node LTS and run:\n"
        "     cd frontend && npx tsc --noEmit\n"
        "   or paste lines 1–94 of the file and I'll fix it by hand."
    )