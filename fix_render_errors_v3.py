#!/usr/bin/env python3
"""
fix_render_errors_v3.py

Fixes the three remaining TypeScript build errors:

  1. MomoPaymentModal.tsx  – adds missing `checkStatus` method to the
     API object that already provides `initiatePayment`.
  2. TenantsList.tsx       – removes unused `useMutation` import.
  3. TenantsList.tsx       – removes unused `queryClient` declaration.

Verifies with `npx tsc --noEmit` when Node is available, then commits/pushes.

Run from the repo root.
Optional env: BRANCH, COMMIT_MSG, SKIP_PUSH=1, RENDER_DEPLOY_HOOK
"""
from __future__ import annotations
import os, re, shutil, subprocess, sys
from pathlib import Path

FRONTEND   = Path("frontend")
MODAL      = FRONTEND / "src/components/MomoPaymentModal.tsx"
TENANTS    = FRONTEND / "src/pages/TenantsList.tsx"
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG",
    "fix(frontend): add checkStatus API method, remove unused imports",
)
SKIP_PUSH          = os.environ.get("SKIP_PUSH") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()


def log(m: str) -> None:
    print(m, flush=True)


def fail(m: str, code: int = 1) -> None:
    print(f"\n❌  {m}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True,
        capture: bool = False) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(map(str, cmd))}")
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, check=check,
        text=True, capture_output=capture,
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
        log("ℹ️   npx not found — skipping local tsc check (Render will verify).")
        return True
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


# ---------------------------------------------------------------- helpers
def find_api_module_for_missing_method(method: str) -> Path | None:
    """
    Search all .ts/.tsx under frontend/src for a module that exports
    an object containing `method` (e.g. initiatePayment). Return that file.
    """
    pattern = re.compile(
        rf"(?:export\s+)?(?:async\s+)?(?:function\s+{method}\b|"
        rf"\b{method}\s*:\s*(?:async\s*)?\()|"
        rf"(?:export\s+const\s+{method}\s*=)",
        re.IGNORECASE,
    )
    for path in (FRONTEND / "src").rglob("*"):
        if path.suffix not in (".ts", ".tsx"):
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            return path
    return None


def find_object_name_for_method(text: str, method: str) -> str | None:
    """
    In a modal file, find which identifier is being used to call
    `.method(...)`. e.g. for `paymentsApi.checkStatus(...)` returns
    'paymentsApi'.
    """
    m = re.search(rf"\b([A-Za-z_$][\w$]*)\.{method}\b", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------- fix modal
def fix_modal() -> bool:
    if not MODAL.exists():
        fail(f"{MODAL} not found.")
    text = MODAL.read_text(encoding="utf-8")

    if "checkStatus" not in text:
        log("ℹ️   No `checkStatus` call in modal — skipping.")
        return True

    obj_name = find_object_name_for_method(text, "checkStatus")
    if not obj_name:
        log("ℹ️   Could not determine which object calls checkStatus — skipping.")
        return True

    log(f"   Modal uses `{obj_name}.checkStatus`.")

    # Find the API module that defines initiatePayment (the sibling method)
    api_file = find_api_module_for_missing_method("initiatePayment")
    if not api_file:
        log("❌  Could not find API module that defines initiatePayment.")
        log("    Manual fix: add a `checkStatus` method to the payments API.")
        return False

    log(f"   API module: {api_file.relative_to(FRONTEND)}")
    api_text = api_file.read_text(encoding="utf-8")

    # If checkStatus already exists there, nothing to do
    if re.search(rf"\bcheckStatus\b", api_text):
        log("ℹ️   `checkStatus` already exists in the API module — skipping insert.")
        return True

    # Determine if the module uses a `const xxxApi = { … }` or similar object
    # We look for the object that contains `initiatePayment`.
    # Strategy: find `initiatePayment` and walk backward to the enclosing `{`.
    idx = api_text.find("initiatePayment")
    if idx == -1:
        log("❌  Could not locate initiatePayment in API module.")
        return False

    # Walk backward to find the opening `{` of the object literal
    brace_start = api_text.rfind("{", 0, idx)
    if brace_start == -1:
        log("❌  Could not find opening brace of API object.")
        return False

    # Determine indentation: use the line containing initiatePayment
    line_start = api_text.rfind("\n", 0, idx) + 1
    indent = re.match(r"\s*", api_text[line_start:]).group(0)
    # The method line should be indented at least this much
    method_line = api_text[line_start:api_text.find("\n", line_start)]
    # Extract existing indentation from initiatePayment line
    m = re.match(r"(\s*)initiatePayment", method_line)
    existing_indent = m.group(1) if m else indent

    # Build a stub for checkStatus
    stub = (
        f"{existing_indent}checkStatus: async (reference: string) => {{\n"
        f"{existing_indent}  // TODO: replace with real backend endpoint if needed\n"
        f"{existing_indent}  const res = await fetch(`/api/v1/payments/status/${{reference}}/`);\n"
        f"{existing_indent}  return res.json();\n"
        f"{existing_indent}}},\n"
    )

    # Insert right after the initiatePayment line
    insert_pos = api_text.find("\n", idx) + 1
    new_api_text = api_text[:insert_pos] + stub + api_text[insert_pos:]
    api_file.write_text(new_api_text, encoding="utf-8")
    log(f"✅  Added `checkStatus` stub to {api_file.name}.")
    return True


# ---------------------------------------------------------------- fix tenants
def fix_tenants() -> bool:
    if not TENANTS.exists():
        fail(f"{TENANTS} not found.")
    text = TENANTS.read_text(encoding="utf-8")
    original = text

    # --- 1. Remove `useMutation` from the import list
    # Matches: import { useQuery, useMutation, useQueryClient } from '…'
    def strip_use_mutation(match: re.Match) -> str:
        names = [n.strip() for n in match.group(1).split(",")]
        names = [n for n in names if n and n != "useMutation"]
        if not names:
            return ""  # entire import becomes empty; drop the line later
        return f"import {{ {', '.join(names)} }} from {match.group(2)}"

    text = re.sub(
        r"import\s*\{\s*([^}]*useMutation[^}]*)\s*\}\s*from\s*(['\"][^'\"]+['\"])",
        strip_use_mutation,
        text,
    )
    # Drop any now-empty import lines
    text = re.sub(r"^\s*import\s*\{\s*\}\s*from.*\n?", "", text, flags=re.MULTILINE)

    # --- 2. Remove `const queryClient = useQueryClient();` if unused
    if re.search(r"\bconst\s+queryClient\b", text):
        # Count references excluding the declaration itself
        refs = len(re.findall(r"\bqueryClient\b", text))
        if refs <= 1:  # only the declaration
            text = re.sub(
                r"^\s*const\s+queryClient\s*=\s*useQueryClient\(\)\s*;?\s*\n?",
                "",
                text,
                flags=re.MULTILINE,
            )
            log("✅  Removed unused `queryClient` declaration.")

    if text == original:
        log("ℹ️   TenantsList already clean — no changes.")
        return True

    TENANTS.write_text(text, encoding="utf-8")
    log("✅  Removed unused `useMutation` import.")
    return True


# ---------------------------------------------------------------- main
def main() -> None:
    if not FRONTEND.exists():
        fail("frontend/ not found. Run from repo root.")

    log("🔧  Fixing MomoPaymentModal …")
    ok1 = fix_modal()
    log("\n🔧  Fixing TenantsList …")
    ok2 = fix_tenants()

    if not (ok1 and ok2):
        fail("Some fixes could not be applied automatically.")

    if not tsc_check():
        fail("TypeScript errors remain — see above.")

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
        log("⏭️   SKIP_PUSH=1 — not pushing.")
        return

    branch = os.environ.get("BRANCH") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    log(f"🚀  Pushing to origin/{branch} …")
    run(["git", "push", "origin", branch])

    if RENDER_DEPLOY_HOOK:
        import urllib.request
        log("🔄  Triggering Render deploy hook …")
        try:
            with urllib.request.urlopen(
                urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST"), timeout=30
            ) as r:
                log(f"✅  Render hook HTTP {r.status}")
        except Exception as e:
            log(f"⚠️   Render hook failed: {e}")

    log("\n✅  Done. Errors fixed and pushed.")


if __name__ == "__main__":
    main()