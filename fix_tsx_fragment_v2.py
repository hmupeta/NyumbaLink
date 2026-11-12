#!/usr/bin/env python3
"""
fix_tsx_fragment_v2.py

Auto-fix TSX where `return (...)` has multiple JSX siblings with no wrapper.
Uses tree-sitter for verification. Brute-forces every (return, </div>) pair
and keeps the one that parses clean. Version-agnostic.

Run from repo root.
"""
from __future__ import annotations
import os, re, subprocess, sys
from pathlib import Path

TARGET = Path("frontend/src/pages/TenantsList.tsx")
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG", "fix(frontend): wrap TenantsList return in fragment"
)
SKIP_PUSH = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()


def log(m): print(m, flush=True)
def fail(m, code=1):
    print(f"\n❌  {m}", file=sys.stderr, flush=True)
    sys.exit(code)


def ensure_parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as ts_ts
    except ImportError:
        log("Installing tree-sitter (one-time)...")
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


def main():
    if not TARGET.exists():
        fail(f"{TARGET} not found. Run from repo root.")
    parser = ensure_parser()

    original_text = TARGET.read_text(encoding="utf-8")
    if not has_errors(parser, original_text.encode("utf-8")):
        log("✅  No syntax errors — nothing to fix.")
        return

    log(f"❌  Syntax errors detected in {TARGET}. Searching for fix...")
    lines = original_text.split("\n")

    return_idxs = [i for i, l in enumerate(lines) if re.search(r"\breturn\s*\(", l)]
    if not return_idxs:
        fail("No `return (` found.")

    fixed = None
    attempts = 0
    for r_idx in reversed(return_idxs):
        for c_idx in range(len(lines) - 1, r_idx, -1):
            if "</div>" not in lines[c_idx]:
                continue
            # try each occurrence of </div> on that line
            for m in re.finditer(r"</div>", lines[c_idx]):
                attempts += 1
                trial = list(lines)
                # wrap the return paren in a fragment
                trial[r_idx] = re.sub(
                    r"\breturn\s*\(",
                    "return (<>",
                    trial[r_idx], count=1,
                )
                # replace this specific </div> with </>
                ln = trial[c_idx]
                trial[c_idx] = ln[:m.start()] + "</>" + ln[m.end():]
                if not has_errors(parser, "\n".join(trial).encode("utf-8")):
                    fixed = (r_idx, c_idx, m.start(), trial)
                    break
            if fixed: break
        if fixed: break

    if not fixed:
        fail(
            f"Tried {attempts} candidate fixes, none produced a clean parse.\n"
            "  The missing/extra tag isn't `</div>` — likely a different\n"
            "  element or a missing `<>` opening tag. Paste lines 1-94\n"
            "  and lines 100-118 and I'll patch by hand."
        )

    r_idx, c_idx, col, new_lines = fixed
    log(f"✅  Fix found ({attempts} candidate{'s' if attempts != 1 else ''} tried):")
    log(f"    line {r_idx + 1}: `return (`  ->  `return (<>`")
    log(f"    line {c_idx + 1}: `</div>`     ->  `</>`")

    TARGET.write_text("\n".join(new_lines), encoding="utf-8")

    # Final verification on the exact bytes written
    if has_errors(parser, TARGET.read_bytes()):
        fail("Verification failed after write — reverting.")
    log("✅  tree-sitter: clean parse.")

    # Commit
    status = subprocess.run(["git", "status", "--porcelain"],
                            check=True, text=True, capture_output=True).stdout.strip()
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
        try:
            with urllib.request.urlopen(
                urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST"), timeout=30
            ) as r:
                log(f"✅  Render hook HTTP {r.status}")
        except Exception as e:
            log(f"⚠️   Render hook failed: {e}")

    log("\n✅  Done. Fix committed and pushed.")


if __name__ == "__main__":
    main()