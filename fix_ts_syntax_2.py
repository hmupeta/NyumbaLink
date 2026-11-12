#!/usr/bin/env python3
"""
fix_ts_syntax.py  (Windows-friendly)

Diagnose and auto-repair common TypeScript syntax errors in
frontend/src/pages/TenantsList.tsx.

Fixes the path bug (parents[2], not parents[1]) and handles npx on Windows.

Usage:
    python fix_ts_syntax.py
Optional env:
    BRANCH              # branch to push (default: current)
    COMMIT_MSG          # commit message
    SKIP_PUSH=1         # don't push
    RENDER_DEPLOY_HOOK  # if set, POST to it after push
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- config
TARGET       = Path("frontend/src/pages/TenantsList.tsx")
FRONTEND_DIR = Path("frontend")          # fixed: contains package.json
COMMIT_MSG   = os.environ.get(
    "COMMIT_MSG", "fix(frontend): repair TS syntax error in TenantsList.tsx"
)
SKIP_PUSH          = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()

ERROR_CONTEXT_BEFORE = 10
ERROR_CONTEXT_AFTER  = 25
ERROR_LINE           = 105   # from the Render log


# ---------------------------------------------------------------- helpers
def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"\n❌  {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def find_npx() -> str:
    """Return the right npx binary for the OS (Windows needs npx.cmd)."""
    for name in ("npx.cmd", "npx"):
        path = shutil.which(name)
        if path:
            return path
    fail("Could not find `npx` on PATH. Is Node.js installed?")


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True,
        capture: bool = False) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(map(str, cmd))}")
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None,
        check=check, text=True, capture_output=capture,
    )


def show_context(path: Path, center: int, before: int, after: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(1, center - before)
    end   = min(len(lines), center + after)
    log(f"\n----- {path} (lines {start}–{end}) -----")
    for i in range(start, end + 1):
        marker = ">>" if i == center else "  "
        log(f"{marker}{i:4} | {lines[i - 1]}")
    log(f"----- end of context ({len(lines)} lines total) -----\n")
    return "\n".join(lines[start - 1:end])


def tsc_check(frontend_dir: Path) -> bool:
    """Run `npx tsc --noEmit` and return True when it passes."""
    npx = find_npx()
    log("🔍  Running TypeScript compiler ...")
    result = subprocess.run(
        [npx, "tsc", "--noEmit"],
        cwd=str(frontend_dir),
        text=True, capture_output=True,
    )
    if result.returncode == 0:
        log("✅  TypeScript check passed.")
        return True
    log("❌  TypeScript errors:")
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    return False


def paren_balance(text: str) -> tuple[int, int, int]:
    """Return (open_paren, close_paren, balance) ignoring nothing fancy."""
    return text.count("("), text.count(")"), text.count("(") - text.count(")")


def auto_repair(text: str) -> str | None:
    """
    Try to fix the two most common 'missing )' patterns at end of file.
    Returns the new text on success, or None if no rule applies.

    Rule 1: file ends inside a `return (` that was never closed  -> append ")"
    Rule 2: file ends inside a JSX block whose last line is `)}` -> not handled,
            return None so the human intervenes.
    """
    open_c, close_c, diff = paren_balance(text)
    tail = "\n".join(text.splitlines()[-30:])

    if diff > 0 and "return (" in tail:
        log(f"🩹  Detected {diff} unclosed '(' after a `return (`. "
            "Appending matching ')' at EOF.")
        return text.rstrip() + "\n" + (")" * diff) + "\n"

    return None


# ---------------------------------------------------------------- main
def main() -> None:
    # -------- sanity checks ----------------------------------------------
    if not TARGET.exists():
        fail(f"{TARGET} not found. Run from the repo root "
             "(the folder that contains both `frontend/` and `manage.py`).")

    if not (FRONTEND_DIR / "package.json").exists():
        fail(f"{FRONTEND_DIR}/package.json not found. "
             "Run the script from the repo root, not from inside frontend/.")

    original = TARGET.read_text(encoding="utf-8")

    # -------- 1. show the area around the error --------------------------
    show_context(TARGET, ERROR_LINE, ERROR_CONTEXT_BEFORE, ERROR_CONTEXT_AFTER)

    open_c, close_c, diff = paren_balance(original)
    log(f"Parens in file: {open_c} open / {close_c} close "
        f"(imbalance = {diff:+d})\n")

    # -------- 2. real tsc run --------------------------------------------
    if tsc_check(FRONTEND_DIR):
        log("ℹ️   TypeScript already passes — nothing to change.")
        return

    # -------- 3. try the auto-repair -------------------------------------
    patched = auto_repair(original)
    if patched is None:
        fail(
            "Could not prove an auto-fixable pattern. Please copy the "
            "context block above (the lines 95–130 of TenantsList.tsx) "
            "into your next message so we can write the exact patch."
        )

    TARGET.write_text(patched, encoding="utf-8")
    log("🔍  Re-running TypeScript compiler after patch ...")
    if not tsc_check(FRONTEND_DIR):
        log("↩️   Patch did not fix it — restoring original file.")
        TARGET.write_text(original, encoding="utf-8")
        fail(
            "Auto-patch failed. The missing `)` is inside a JSX block or "
            "a .map() callback, not at EOF. Please paste the context "
            "block above and we'll patch it precisely."
        )
    log("✅  Patch fixed the TypeScript error.")

    # -------- 4. commit & push -------------------------------------------
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
        log("⏭️   SKIP_PUSH=1 — not pushing.")
        return

    branch = os.environ.get("BRANCH") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    log(f"🚀  Pushing to origin/{branch} ...")
    run(["git", "push", "origin", branch])

    # -------- 5. optional Render deploy hook -----------------------------
    if RENDER_DEPLOY_HOOK:
        import urllib.request
        log("🔄  Triggering Render deploy hook ...")
        req = urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                log(f"✅  Render hook returned HTTP {resp.status}.")
        except Exception as exc:  # noqa: BLE001
            log(f"⚠️   Render hook failed: {exc}")

    log("\n✅  Done. Fix committed and pushed.")


if __name__ == "__main__":
    main()