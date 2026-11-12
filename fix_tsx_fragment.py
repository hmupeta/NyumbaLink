#!/usr/bin/env python3
"""
fix_tsx_fragment.py

Auto-fixes TSX where a component's `return (...)` has multiple JSX siblings
with no wrapper (classic TS1005 / TS1128 / TS1109 trio).

Fix applied:
    return (              ->  return (<>
      <div>...</div>            <div>...</div>
      {cond && <M />}           {cond && <M />}
      </div>   (orphan)     ->  </>
    )                         )

Uses tree-sitter to locate the orphan close tag AND to verify the fix
before committing. Rolls back on any doubt.

Run from repo root:
    python fix_tsx_fragment.py
Optional env:
    BRANCH, COMMIT_MSG, SKIP_PUSH=1, RENDER_DEPLOY_HOOK
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
from pathlib import Path

TARGET = Path("frontend/src/pages/TenantsList.tsx")
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG", "fix(frontend): wrap TenantsList return in fragment"
)
SKIP_PUSH = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()


def log(m: str) -> None:
    print(m, flush=True)


def fail(m: str, code: int = 1) -> None:
    print(f"\n❌  {m}", file=sys.stderr, flush=True)
    sys.exit(code)


def ensure_parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as ts_ts
    except ImportError:
        log("Installing tree-sitter (one-time)...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "tree-sitter", "tree-sitter-typescript",
        ])
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as ts_ts
    tsx = Language(ts_ts.language_tsx())
    try:
        return Parser(tsx)
    except TypeError:               # older tree-sitter API
        p = Parser()
        p.set_language(tsx)
        return p


def collect_errors(parser, data: bytes):
    tree = parser.parse(data)
    out = []

    def walk(n):
        if n.type == "ERROR" or n.is_missing:
            out.append(n)
        for c in n.children:
            walk(c)

    walk(tree.root_node)
    return out


def main() -> None:
    if not TARGET.exists():
        fail(f"{TARGET} not found. Run from repo root.")

    parser = ensure_parser()
    original = TARGET.read_text(encoding="utf-8")
    original_bytes = original.encode("utf-8")

    errs = collect_errors(parser, original_bytes)
    if not errs:
        log("✅  No syntax errors — nothing to fix.")
        return

    log(f"❌  {len(errs)} syntax error(s) found — attempting fix.")

    # 1. Locate the orphan </div> from an ERROR node
    orphan_line = None
    for err in errs:
        text = original_bytes[err.start_byte:err.end_byte].decode("utf-8")
        m = re.search(r"</div\s*>", text)
        if m:
            start_line = err.start_point[0]        # 0-based
            line_in_err = text[:m.start()].count("\n")
            orphan_line = start_line + line_in_err
            break

    if orphan_line is None:
        fail(
            "Could not identify an orphan `</div>` in an error node.\n"
            "  This script only handles a stray `</div>`; other stray tags\n"
            "  must be fixed manually."
        )

    # 2. Try every `return (` above the orphan; pick the one that parses clean
    lines = original.split("\n")
    candidates = [
        i for i, ln in enumerate(lines)
        if "return (" in ln and i < orphan_line
    ]
    if not candidates:
        fail("No `return (` found above the orphan.")

    chosen_return_line = None
    fixed_lines = None
    for return_line in reversed(candidates):        # nearest first
        trial = lines.copy()
        trial[return_line] = trial[return_line].replace(
            "return (", "return (<>", 1
        )
        trial[orphan_line] = re.sub(
            r"</div\s*>", "</>", trial[orphan_line], count=1
        )
        if not collect_errors(parser, "\n".join(trial).encode("utf-8")):
            chosen_return_line = return_line
            fixed_lines = trial
            break

    if fixed_lines is None:
        fail(
            "Auto-fix did not produce a clean parse. Manual fix:\n"
            f"  1. line {orphan_line + 1}: change `</div>`  ->  `</>`\n"
            "  2. the enclosing `return (` line:  `return (`  ->  `return (<>`\n"
            "  Together these wrap the return value in a JSX fragment."
        )

    log(f"  Fixed `return (` at line {chosen_return_line + 1}")
    log(f"  Replaced orphan `</div>` at line {orphan_line + 1} with `</>`")
    log("✅  tree-sitter verification: clean parse.")

    TARGET.write_text("\n".join(fixed_lines), encoding="utf-8")

    # 3. Commit + push
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    if not status:
        log("ℹ️   No changes to commit.")
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

    log(f"🚀  Pushing to origin/{branch}...")
    subprocess.run(["git", "push", "origin", branch], check=True)

    if RENDER_DEPLOY_HOOK:
        import urllib.request
        log("🔄  Triggering Render deploy hook...")
        req = urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                log(f"✅  Render hook HTTP {resp.status}")
        except Exception as exc:
            log(f"⚠️   Render hook failed: {exc}")

    log("\n✅  Done. Fix committed and pushed.")


if __name__ == "__main__":
    main()