#!/usr/bin/env python3
"""
diagnose_tsx.py

Find TSX/TypeScript syntax errors WITHOUT Node.js.

- Lexes the file, ignoring strings, template literals and comments.
- Reports every bracket mismatch `(`, `{`, `[` with line/col.
- Reports every bracket left open at EOF.
- Prints a side-by-side "expected vs actual" for the first failure.
- `--diff` shows recent git changes to the file so you can see what broke.

Usage:
    python diagnose_tsx.py
    python diagnose_tsx.py --file frontend/src/pages/TenantsList.tsx
    python diagnose_tsx.py --diff --rev HEAD~5
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_FILE = Path("frontend/src/pages/TenantsList.tsx")
OPENERS = {"(": ")", "{": "}", "[": "]"}
CLOSERS = {v: k for k, v in OPENERS.items()}


# --------------------------------------------------------------------------- #
# Lexer + bracket checker
# --------------------------------------------------------------------------- #
def lex_and_check(text: str):
    """
    Walk the text, skip strings / template literals / comments, and track
    bracket balance.  Returns (errors, open_stack).
    """
    errors: list[str] = []
    stack: list[tuple[str, int, int, str]] = []  # (bracket, line, col, snippet)

    line = 1
    col = 1
    i = 0
    n = len(text)
    line_start = 0

    def snippet(ln: int) -> str:
        end = text.find("\n", line_start)
        if end == -1:
            end = n
        return text[line_start:end]

    while i < n:
        c = text[i]

        # newline
        if c == "\n":
            line += 1
            col = 1
            i += 1
            line_start = i
            continue

        # line comment
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue

        # block comment
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    line += 1
                    line_start = i + 1
                i += 1
            i += 2
            continue

        # string / template literal
        if c in ('"', "'", "`"):
            q = c
            start_line, start_col = line, col
            i += 1
            col += 1
            while i < n and text[i] != q:
                if text[i] == "\\":
                    i += 2
                    col += 2
                    continue
                if text[i] == "\n":
                    if q != "`":
                        errors.append(
                            f"Line {start_line}:{start_col}: unterminated "
                            f"string literal"
                        )
                    line += 1
                    col = 1
                    line_start = i + 1
                    i += 1
                    continue
                i += 1
                col += 1
            i += 1
            col += 1
            continue

        # opener
        if c in OPENERS:
            stack.append((c, line, col, snippet(line)))
            i += 1
            col += 1
            continue

        # closer
        if c in CLOSERS:
            if not stack:
                errors.append(
                    f"Line {line}:{col}: unexpected '{c}' — nothing to close"
                )
            elif stack[-1][0] != CLOSERS[c]:
                top, tl, tc, _ = stack[-1]
                errors.append(
                    f"Line {line}:{col}: got '{c}' but expected "
                    f"'{OPENERS[top]}' to close '{top}' opened at "
                    f"{tl}:{tc}"
                )
                # pop the wrong top so we can keep going
                stack.pop()
            else:
                stack.pop()
            i += 1
            col += 1
            continue

        i += 1
        col += 1

    return errors, stack


# --------------------------------------------------------------------------- #
# Pretty printing helpers
# --------------------------------------------------------------------------- #
def print_context(path: Path, line_no: int, pad: int = 6) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(1, line_no - pad)
    end = min(len(lines), line_no + pad)
    print(f"\n----- {path} lines {start}-{end} -----")
    for i in range(start, end + 1):
        marker = ">>" if i == line_no else "  "
        print(f"{marker}{i:4} | {lines[i - 1]}")
    print("----- end -----\n")


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, check=False, text=True, capture_output=True
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("--diff", action="store_true",
                    help="also show git log + diff of this file")
    ap.add_argument("--rev", default="HEAD~10",
                    help="git revision to diff against (default: HEAD~10)")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"❌  {args.file} not found", file=sys.stderr)
        sys.exit(1)

    text = args.file.read_text(encoding="utf-8")
    print(f"🔍  Lexing {args.file} ({len(text.splitlines())} lines)...")

    errors, open_stack = lex_and_check(text)

    if errors:
        print("\n❌  Bracket errors found:\n")
        for e in errors:
            print(f"   {e}")
        # Show context around the first error
        first_line = int(errors[0].split(":")[0].replace("Line ", ""))
        print_context(args.file, first_line)
        print("\n👉  Fix the mismatched bracket above, then re-run.")
        print("    (You do NOT need Node.js — just edit the file and save.)")
    elif open_stack:
        print("\n❌  Unclosed brackets at EOF:\n")
        for b, ln, cl, snip in open_stack:
            print(f"   Line {ln}:{cl}: '{b}' was never closed")
            print(f"      {snip.strip()[:120]}")
        print_context(args.file, open_stack[0][1])
        print("\n👉  Add the missing closing bracket(s).")
    else:
        print("✅  All brackets and string literals balance.")

    if args.diff:
        print(f"\n🔎  Recent changes to {args.file}:")
        log = run_git([
            "log", "--oneline", "--no-decorate",
            f"{args.rev}..HEAD", "--", str(args.file),
        ])
        if log.stdout.strip():
            print(log.stdout)
            diff = run_git(["diff", f"{args.rev}", "--", str(args.file)])
            print(diff.stdout)
        else:
            print(f"   (no commits touching this file since {args.rev})")

    if not errors and not open_stack:
        print(
            "\nℹ️   Brackets are balanced — the TS error is likely inside "
            "a JSX *tag* (e.g. an extra `</div>` or a missing `<div>`) "
            "or a template-literal edge case.\n"
            "   Run again with `--diff` to see what recently changed, "
            "or paste lines 1-94 of the file and I'll pinpoint it."
        )


if __name__ == "__main__":
    main()