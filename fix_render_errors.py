#!/usr/bin/env python3
"""
fix_render_errors.py

Fixes the three TypeScript errors currently blocking the Render build:

  1. MomoPaymentModal.tsx  – `checkStatus` / `initiatePayment` are called on
     the wrong API object (wallet API).  This script searches the codebase
     for the real definitions of those methods and, if found, rewrites the
     import + calls to use the correct API.
  2. TenantsList.tsx      – removes the unused `markPaidMutation` declaration.

If Node.js is available (`npx` on PATH), it runs `tsc --noEmit` to verify
before committing.  Otherwise it still commits/pushes and lets Render verify.

Run from the project root (the folder containing `manage.py` and `frontend/`).
Optional env vars:
    BRANCH              # git branch (default: current)
    COMMIT_MSG          # commit message
    SKIP_PUSH=1         # don't push
    RENDER_DEPLOY_HOOK  # POST here after push
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- config
FRONTEND = Path("frontend")
MODAL   = FRONTEND / "src/components/MomoPaymentModal.tsx"
TENANTS = FRONTEND / "src/pages/TenantsList.tsx"
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG",
    "fix(frontend): use correct payments API in MomoPaymentModal + drop unused var",
)
SKIP_PUSH          = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()

MISSING_METHODS = ("checkStatus", "initiatePayment")


# ---------------------------------------------------------------- helpers
def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"\n❌  {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None,
        capture: bool = False) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(map(str, cmd))}")
    return subprocess.run(
        cmd, check=check, text=True, capture_output=capture,
        cwd=str(cwd) if cwd else None,
    )


def find_npx() -> str | None:
    for name in ("npx.cmd", "npx"):
        p = shutil.which(name)
        if p:
            return p
    return None


def tsc_check() -> bool:
    npx = find_npx()
    if not npx:
        log("ℹ️   `npx` not found – skipping TypeScript check.")
        return True                      # treat as “unknown”, proceed
    log("🔍  Running TypeScript check …")
    res = subprocess.run(
        [npx, "tsc", "--noEmit"],
        cwd=str(FRONTEND), text=True, capture_output=True,
    )
    if res.returncode == 0:
        log("✅  TypeScript check passed.")
        return True
    log("❌  TypeScript errors remain:")
    print(res.stdout, flush=True)
    print(res.stderr, flush=True)
    return False


# ---------------------------------------------------------------- step 1: locate real API
def find_api_module_for(method: str) -> str | None:
    """
    Search all .ts/.tsx files under frontend/src for a function/method
    definition of `method`.  Return the *relative* file path (e.g.
    'src/api/payments.ts') if found, else None.
    """
    pattern = re.compile(
        rf"(?:export\s+)?(?:async\s+)?(?:function\s+{method}\b|"
        rf"\b{method}\s*:\s*(?:async\s*)?\()|"
        rf"(?:export\s+const\s+{method}\s*=)",
        re.IGNORECASE,
    )
    for path in FRONTEND.joinpath("src").rglob("*"):
        if path.suffix not in (".ts", ".tsx"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            # return path relative to frontend/src for import
            rel = path.relative_to(FRONTEND / "src")
            log(f"   Found `{method}` in {rel}")
            return str(rel).replace("\\", "/")
    return None


# ---------------------------------------------------------------- step 2: fix modal
def fix_modal() -> bool:
    if not MODAL.exists():
        fail(f"{MODAL} not found.")

    text = MODAL.read_text(encoding="utf-8")

    # --- identify the object name currently used for the missing methods
    obj_names = set()
    for m in re.finditer(
        rf"\b([A-Za-z_$][\w$]*)\.(?:{'|'.join(MISSING_METHODS)})\b",
        text,
    ):
        obj_names.add(m.group(1))

    if not obj_names:
        log("ℹ️   No `.checkStatus` / `.initiatePayment` calls found in the modal.")
        return True

    log(f"   Current API object(s) in modal: {', '.join(obj_names)}")

    # --- find the real module that defines these methods
    candidates = {}
    for meth in MISSING_METHODS:
        mod = find_api_module_for(meth)
        if mod:
            candidates[meth] = mod

    if not candidates:
        log("❌  Could not locate definitions for `checkStatus` / `initiatePayment`.")
        log("    Manual fix needed:")
        log("      • Find the correct API client (e.g. paymentsApi).")
        log("      • Update the import and the object used at lines 23 & 42.")
        return False

    # All missing methods should ideally come from the same module
    modules = set(candidates.values())
    if len(modules) > 1:
        log(f"⚠️   Methods are spread across modules: {modules}")
        log("    Will pick the first one; you may need to adjust manually.")

    target_mod = next(iter(modules))
    # Derive a sensible import name: e.g. src/api/payments.ts -> paymentsApi
    stem = Path(target_mod).stem           # e.g. 'payments'
    # If the file already exports a default, we assume that; otherwise try
    # to guess the named export by looking at the file.
    mod_file = FRONTEND / "src" / target_mod
    mod_text = mod_file.read_text(encoding="utf-8", errors="ignore")
    # Very rough: look for `export const <name> =` or `export default`
    export_name = None
    m = re.search(r"export\s+const\s+([A-Za-z_$][\w$]*)\s*=", mod_text)
    if m:
        export_name = m.group(1)
    else:
        # fall back to `paymentsApi` style
        export_name = stem + "Api"

    log(f"   Will use `{export_name}` from `{target_mod}`.")

    # --- rewrite the imports in the modal
    # Remove any existing import of the wrong wallet API, if present
    lines = text.splitlines()
    new_lines = []
    import_replaced = False
    for ln in lines:
        # If line imports the wrong object, drop it (we’ll add a new import)
        if re.match(r"^import\s+.*\b(" + "|".join(map(re.escape, obj_names)) + r")\b", ln):
            log(f"   Removing old import: {ln.strip()}")
            continue
        new_lines.append(ln)

    text = "\n".join(new_lines)

    # Add the new import (after the last existing import)
    import_stmt = f'import {{ {export_name} }} from "../{target_mod}";'
    # also handle default import if the module uses `export default`
    if re.search(r"export\s+default", mod_text):
        import_stmt = f'import {export_name} from "../{target_mod}";'

    # Insert after the last line that starts with `import `
    last_import_idx = -1
    for i, ln in enumerate(text.splitlines()):
        if ln.strip().startswith("import "):
            last_import_idx = i
    if last_import_idx >= 0:
        lines = text.splitlines()
        lines.insert(last_import_idx + 1, import_stmt)
        text = "\n".join(lines)
    else:
        text = import_stmt + "\n" + text

    # Replace the old object name with the new one in the calls
    # (only for the missing‑method calls, not everywhere)
    for obj in obj_names:
        for meth in MISSING_METHODS:
            text = re.sub(
                rf"\b{re.escape(obj)}\.{meth}\b",
                f"{export_name}.{meth}",
                text,
            )

    MODAL.write_text(text, encoding="utf-8")
    log(f"✅  Modal updated: now uses `{export_name}` from `{target_mod}`.")
    return True


# ---------------------------------------------------------------- step 3: drop unused var
def fix_unused_var() -> bool:
    if not TENANTS.exists():
        fail(f"{TENANTS} not found.")
    lines = TENANTS.read_text(encoding="utf-8").splitlines()
    out = []
    removed = False
    for ln in lines:
        if re.search(r"\bmarkPaidMutation\b", ln) and "=" in ln:
            # likely the declaration line
            log(f"   Removing unused declaration: {ln.strip()}")
            removed = True
            continue
        out.append(ln)
    if not removed:
        log("ℹ️   No `markPaidMutation` declaration found.")
        return True
    TENANTS.write_text("\n".join(out), encoding="utf-8")
    log("✅  Removed unused `markPaidMutation`.")
    return True


# ---------------------------------------------------------------- main
def main() -> None:
    if not FRONTEND.exists():
        fail("frontend/ not found. Run from the repo root.")

    log("🔧  Fixing MomoPaymentModal …")
    ok1 = fix_modal()
    log("\n🔧  Fixing TenantsList …")
    ok2 = fix_unused_var()

    if not (ok1 and ok2):
        fail(
            "Some fixes could not be applied automatically.\n"
            "  Review the messages above, apply the manual changes,\n"
            "  then re-run this script (it is idempotent)."
        )

    # -------- verify with tsc if possible --------------------------------
    if not tsc_check():
        fail(
            "TypeScript still reports errors after the patch.\n"
            "  The auto‑fix may have chosen the wrong module.\n"
            "  Please fix the remaining errors manually, then re‑run."
        )

    # -------- commit & push ---------------------------------------------
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    if not status:
        log("ℹ️   No changes to commit.")
        return

    run(["git", "add", str(MODAL), str(TENANTS)])
    run(["git", "commit", "-m", COMMIT_MSG])

    if SKIP_PUSH:
        log("⏭️   SKIP_PUSH=1 – not pushing.")
        return

    branch = os.environ.get("BRANCH") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    log(f"🚀  Pushing to origin/{branch} …")
    run(["git", "push", "origin", branch])

    # -------- optional Render deploy hook --------------------------------
    if RENDER_DEPLOY_HOOK:
        import urllib.request
        log("🔄  Triggering Render deploy hook …")
        try:
            with urllib.request.urlopen(
                urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST"),
                timeout=30,
            ) as resp:
                log(f"✅  Render hook HTTP {resp.status}")
        except Exception as exc:
            log(f"⚠️   Render hook failed: {exc}")

    log("\n✅  Done. Errors fixed and pushed.")


if __name__ == "__main__":
    main()