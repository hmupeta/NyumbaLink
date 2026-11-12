#!/usr/bin/env python3
"""
fix_ts_syntax.py

Diagnose and auto-repair common TypeScript syntax errors in
frontend/src/pages/TenantsList.tsx that cause:
    TS1005: ')' expected
    TS1128: Declaration or statement expected
    TS1109: Expression expected

Strategy:
  1. Print the lines around the reported error (default 100-120).
  2. Run `npx tsc --noEmit` to get the exact error locations.
  3. If the file has an unbalanced `return (` at the end,
     append the missing `)` and re‑check.
  4. If the build succeeds, commit and push the change.

Usage:
    python fix_ts_syntax.py
Optional environment variables:
    BRANCH              # git branch to push (default: current branch)
    COMMIT_MSG          # override commit message
    SKIP_PUSH=1         # do not push
    RENDER_DEPLOY_HOOK  # if set, curl the Render deploy hook
"""

from __future__ import annotations
import os, re, subprocess, sys
from pathlib import Path

TARGET = Path("frontend/src/pages/TenantsList.tsx")
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG", "fix(frontend): repair TS syntax error in TenantsList.tsx"
)
SKIP_PUSH = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()
ERROR_RANGE = (95, 125)   # print lines around the reported error


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"❌  {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd: list[str], *, check: bool = True, capture: bool = False):
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd, check=check, text=True, capture_output=capture
    )


def show_context(path: Path, start: int, end: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    log(f"\n--- {path} lines {start}–{end} ---")
    for i, line in enumerate(lines, start=1):
        if start <= i <= end:
            log(f"{i:4} | {line}")
    log("-----------------------------------\n")


def tsc_check(frontend_dir: Path) -> bool:
    """Run `npx tsc --noEmit` and return True if no errors."""
    log("🔍  Running TypeScript compiler ...")
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=frontend_dir,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        log("✅  TypeScript check passed.")
        return True
    log("❌  TypeScript errors:")
    print(result.stdout, flush=True)
    print(result.stderr, flush=True)
    return False


def has_unbalanced_return(text: str) -> bool:
    """
    Heuristic: the file ends with `return (` but the total number of
    '(' exceeds ')' by one or more, and the last non‑blank line does
    not close the return.
    """
    # Count parentheses, ignoring those inside strings is overkill for this
    open_count = text.count("(")
    close_count = text.count(")")
    # If the file already has balanced parens, skip
    if open_count <= close_count:
        return False
    # Make sure a `return (` exists near the end
    tail = "\n".join(text.splitlines()[-20:])
    return "return (" in tail


def main() -> None:
    if not TARGET.exists():
        fail(f"{TARGET} not found. Run from the project root.")

    frontend_dir = TARGET.parents[1]  # frontend/
    if not (frontend_dir / "package.json").exists():
        fail(f"{frontend_dir}/package.json not found.")

    text = TARGET.read_text(encoding="utf-8")

    # 1️⃣ Show the problematic region
    show_context(TARGET, *ERROR_RANGE)

    # 2️⃣ Run tsc to see the exact errors
    ok = tsc_check(frontend_dir)
    if ok:
        log("ℹ️   TypeScript already passes — nothing to fix.")
        return

    # 3️⃣ Attempt automatic repair (append missing ')')
    if has_unbalanced_return(text):
        log("🩹  Detected unbalanced `return (` – appending missing `)` at EOF.")
        new_text = text.rstrip() + "\n)\n"
        TARGET.write_text(new_text, encoding="utf-8")
        log("🔍  Re‑running TypeScript compiler after patch ...")
        if tsc_check(frontend_dir):
            log("✅  Patch succeeded.")
            text = new_text
        else:
            log("❌  Patch did not resolve the error. Restoring original file.")
            TARGET.write_text(text, encoding="utf-8")
            fail(
                "Automatic repair failed. Please share the lines "
                f"{ERROR_RANGE[0]}–{ERROR_RANGE[1]} of {TARGET} so we can "
                "write a precise fix."
            )
    else:
        fail(
            "Could not automatically detect the missing parenthesis. "
            f"Please share the lines {ERROR_RANGE[0]}–{ERROR_RANGE[1]} of "
            f"{TARGET}."
        )

    # 4️⃣ Commit & push
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()

    if not status:
        log("ℹ️   No changes to commit.")
    else:
        run(["git", "add", str(TARGET)])
        run(["git", "commit", "-m", COMMIT_MSG])

    if SKIP_PUSH:
        log("⏭️   SKIP_PUSH=1 – not pushing.")
        return

    branch = os.environ.get("BRANCH") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    log(f"🚀  Pushing to origin/{branch} ...")
    run(["git", "push", "origin", branch])

    if RENDER_DEPLOY_HOOK:
        log("🔄  Triggering Render deploy hook ...")
        import urllib.request
        req = urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                log(f"✅  Render hook returned HTTP {resp.status}.")
        except Exception as exc:
            log(f"⚠️   Render hook failed: {exc}")

    log("\n✅  Done. The syntax error should be fixed and pushed.")


if __name__ == "__main__":
    main()