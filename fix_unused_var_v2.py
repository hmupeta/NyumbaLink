#!/usr/bin/env python3
"""
fix_unused_var_v2.py

Fixes the leftover `markPaidMutation` fragment in TenantsList.tsx.

The previous fixer removed only the first line of a multi-line
`const markPaidMutation = useMutation({ ... })` declaration, leaving
the options object orphaned (TS1005 / TS1128).

This script:
  1. Finds the most recent commit where TenantsList.tsx parses cleanly.
  2. In that version, locates the FULL markPaidMutation declaration
     using brace/paren matching (multi-line aware).
  3. Removes that whole span.
  4. Verifies the result with tree-sitter.
  5. Commits and pushes.

Run from the repo root.
Optional env: BRANCH, COMMIT_MSG, SKIP_PUSH=1, RENDER_DEPLOY_HOOK
"""
from __future__ import annotations
import os, re, subprocess, sys
from pathlib import Path

TARGET = Path("frontend/src/pages/TenantsList.tsx")
VAR_NAME = "markPaidMutation"
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG",
    "fix(frontend): properly remove unused markPaidMutation declaration",
)
SKIP_PUSH          = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()


def log(m): print(m, flush=True)
def fail(m, code=1):
    print(f"\n❌  {m}", file=sys.stderr, flush=True)
    sys.exit(code)


# ---------------------------------------------------------------- tree-sitter
def ensure_parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as ts_ts
    except ImportError:
        log("Installing tree-sitter (one-time)…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                               "tree-sitter", "tree-sitter-typescript"])
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as ts_ts
    tsx = Language(ts_ts.language_tsx())
    try:
        return Parser(tsx)
    except TypeError:
        p = Parser(); p.set_language(tsx); return p


def has_errors(parser, data: bytes) -> bool:
    tree = parser.parse(data)
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or n.is_missing:
            return True
        stack.extend(n.children)
    return False


# ---------------------------------------------------------------- helpers
def git_show(rev: str) -> str | None:
    res = subprocess.run(
        ["git", "show", f"{rev}:{TARGET.as_posix()}"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return None
    return res.stdout


def find_declaration_span(lines: list[str], name: str):
    """
    Find the full span (start_line, end_line, inclusive) of a
    `const|let|var name = ... ` declaration, handling multi-line
    object literals / calls.  Returns None if not found.
    """
    start = None
    for i, ln in enumerate(lines):
        if re.search(rf"\b(?:const|let|var)\s+{re.escape(name)}\b", ln):
            start = i
            break
    if start is None:
        return None

    depth = 0
    saw_open = False
    for i in range(start, len(lines)):
        ln = lines[i]
        depth += (ln.count("{") + ln.count("(") + ln.count("["))
        depth -= (ln.count("}") + ln.count(")") + ln.count("]"))
        if depth > 0:
            saw_open = True
        if saw_open and depth <= 0:
            return (start, i)
        if not saw_open and ln.rstrip().endswith(";"):
            # simple single-line declaration like `const x = 1;`
            return (start, i)
    return (start, len(lines) - 1)


# ---------------------------------------------------------------- main
def main():
    if not TARGET.exists():
        fail(f"{TARGET} not found. Run from repo root.")

    parser = ensure_parser()

    log("📜  Recent commits touching TenantsList.tsx:")
    subprocess.run(
        ["git", "log", "--oneline", "-8", "--", TARGET.as_posix()],
        check=False,
    )

    # 1. Walk back until we find a version of this file that parses cleanly.
    good_rev, good_text = None, None
    for n in range(1, 25):
        rev = f"HEAD~{n}"
        text = git_show(rev)
        if text is None:
            break
        if not has_errors(parser, text.encode("utf-8")):
            good_rev, good_text = rev, text
            break

    if good_text is None:
        # Even HEAD~n fails — try the working copy itself
        current = TARGET.read_text(encoding="utf-8")
        if not has_errors(parser, current.encode("utf-8")):
            log("✅  Current working copy is already clean — nothing to do.")
            return
        fail(
            "Could not find a syntactically-clean version of the file in the last 25 commits.\n"
            "  Please paste lines 1-30 of frontend/src/pages/TenantsList.tsx."
        )

    log(f"✅  Found known-good version at {good_rev}")

    # 2. Find full markPaidMutation declaration in the good version
    good_lines = good_text.splitlines()
    span = find_declaration_span(good_lines, VAR_NAME)

    if span is None:
        log(f"ℹ️   No `{VAR_NAME}` declaration in {good_rev} — using it as-is.")
        fixed_text = good_text
    else:
        start, end = span
        log(f"   `{VAR_NAME}` declaration occupies lines {start+1}-{end+1} "
            f"of the good version ({end-start+1} line(s))")
        new_lines = good_lines[:start] + good_lines[end+1:]
        # preserve trailing newline
        fixed_text = "\n".join(new_lines)
        if good_text.endswith("\n") and not fixed_text.endswith("\n"):
            fixed_text += "\n"

    # 3. Verify
    if has_errors(parser, fixed_text.encode("utf-8")):
        # Show lines 1-30 of the bad result so we can debug
        print("\n----- repaired file, lines 1-30 (still has errors) -----")
        for i, ln in enumerate(fixed_text.splitlines()[:30], 1):
            print(f"{i:4} | {ln}")
        print("----- end -----\n")
        fail("Repair did not produce a clean parse. "
             "Paste the lines above and we'll fix by hand.")

    log("✅  tree-sitter: repaired file parses cleanly.")

    # 4. Write
    TARGET.write_text(fixed_text, encoding="utf-8")

    # 5. Commit + push
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    if not status:
        log("ℹ️   No changes to commit (file was already clean).")
        return

    subprocess.run(["git", "add", str(TARGET)], check=True)
    subprocess.run(["git", "commit", "-m", COMMIT_MSG], check=True)

    if SKIP_PUSH:
        log("⏭️   SKIP_PUSH=1 — not pushing.")
        return

    branch = os.environ.get("BRANCH") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    log(f"🚀  Pushing to origin/{branch}…")
    subprocess.run(["git", "push", "origin", branch], check=True)

    if RENDER_DEPLOY_HOOK:
        import urllib.request
        log("🔄  Triggering Render deploy hook…")
        try:
            with urllib.request.urlopen(
                urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST"), timeout=30
            ) as r:
                log(f"✅  Render hook HTTP {r.status}")
        except Exception as e:
            log(f"⚠️   Render hook failed: {e}")

    log("\n✅  Done. TenantsList.tsx is syntactically clean and pushed.")


if __name__ == "__main__":
    main()