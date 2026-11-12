#!/usr/bin/env python3
"""
fix_momo_callback.py

Idempotently adds the missing `momo_callback` view to apps/payments/views.py,
runs `python manage.py check`, then commits and pushes to GitHub.

Usage:
    python fix_momo_callback.py

Optional environment variables:
    BRANCH              # git branch to push to (default: current branch)
    COMMIT_MSG          # commit message override
    SKIP_PUSH=1         # do not push (dry run)
    SKIP_CHECK=1        # skip `manage.py check` (not recommended)
    RENDER_DEPLOY_HOOK  # if set, curl the Render deploy hook after push
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- config
VIEWS_FILE = Path("apps/payments/views.py")
URLS_FILE = Path("apps/payments/urls.py")
COMMIT_MSG = os.environ.get(
    "COMMIT_MSG", "fix(payments): add missing momo_callback view"
)
SKIP_PUSH = os.environ.get("SKIP_PUSH") == "1"
SKIP_CHECK = os.environ.get("SKIP_CHECK") == "1"
RENDER_DEPLOY_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "").strip()

VIEW_SNIPPET = '''

# --- Added by fix_momo_callback.py -----------------------------------------
# These imports are safe to duplicate; Python ignores repeat imports.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def momo_callback(request):
    """
    Webhook endpoint for MTN MoMo (or other mobile-money) payment callbacks.

    TODO: verify the provider signature, look up the Payment/Order record,
          and update its status inside a transaction.atomic() block.
    """
    return JsonResponse({"status": "received"}, status=200)
# ---------------------------------------------------------------------------
'''


# ---------------------------------------------------------------- helpers
def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str, code: int = 1) -> "None":
    print(f"❌  {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess, printing the command for transparency."""
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def current_branch() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    return out


# ---------------------------------------------------------------- main
def main() -> None:
    # ---- pre-flight checks ------------------------------------------------
    if not Path("manage.py").exists():
        fail("manage.py not found. Run from your Django project root.")

    if not VIEWS_FILE.exists():
        fail(f"{VIEWS_FILE} not found.")

    if not URLS_FILE.exists():
        fail(f"{URLS_FILE} not found.")

    # ---- 1. add view idempotently ----------------------------------------
    text = VIEWS_FILE.read_text(encoding="utf-8")

    if re.search(r"^def momo_callback\b", text, flags=re.MULTILINE):
        log(f"ℹ️   momo_callback already defined in {VIEWS_FILE} — skipping insert.")
    else:
        log(f"➕  Appending momo_callback to {VIEWS_FILE} ...")
        with VIEWS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(VIEW_SNIPPET)

    # ---- 2. Django system check ------------------------------------------
    if SKIP_CHECK:
        log("⏭️   SKIP_CHECK=1 — skipping `manage.py check`.")
    else:
        log("🔍  Running Django system check ...")
        # Prefer the venv python if it exists
        python_bin = (
            str(Path(".venv/bin/python"))
            if Path(".venv/bin/python").exists()
            else sys.executable
        )
        try:
            run([python_bin, "manage.py", "check"])
        except subprocess.CalledProcessError:
            fail(
                "Django `manage.py check` failed. Fix the error above, "
                "then re-run this script. (Tip: stale __pycache__? run "
                "`find . -name __pycache__ -type d -exec rm -rf {} +`.)"
            )

    # ---- 3. git status / commit ------------------------------------------
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()

    if not status:
        log("ℹ️   No changes to commit.")
    else:
        run(["git", "add", str(VIEWS_FILE)])
        run(["git", "commit", "-m", COMMIT_MSG])

    # ---- 4. push ---------------------------------------------------------
    if SKIP_PUSH:
        log("⏭️   SKIP_PUSH=1 — not pushing.")
        return

    branch = os.environ.get("BRANCH") or current_branch()
    log(f"🚀  Pushing to origin/{branch} ...")
    run(["git", "push", "origin", branch])

    # ---- 5. optional Render deploy hook ---------------------------------
    if RENDER_DEPLOY_HOOK:
        log("🔄  Triggering Render deploy hook ...")
        import urllib.request

        req = urllib.request.Request(RENDER_DEPLOY_HOOK, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if 200 <= resp.status < 300:
                    log("✅  Render deploy triggered.")
                else:
                    log(f"⚠️   Render hook returned HTTP {resp.status}.")
        except Exception as exc:  # noqa: BLE001
            log(f"⚠️   Render hook failed: {exc}")
    else:
        log(
            "ℹ️   No RENDER_DEPLOY_HOOK set — Render will auto-deploy on push "
            "if Auto-Deploy is enabled."
        )

    log("")
    log(f"✅  Done. momo_callback is defined and pushed to origin/{branch}.")


if __name__ == "__main__":
    main()