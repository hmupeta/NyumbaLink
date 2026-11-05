#!/usr/bin/env python3
"""Portable Node.js v26.13.0 setup for NyumbaLink Phase 3a frontend.

No installer, no admin rights, no global PATH changes.
Everything lives under tools/ inside the project.
"""
from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path.cwd()
TOOLS = ROOT / "tools"

NODE_VERSION = "v26.13.0"
# SHA256 for the official win-x64 ZIP. If you re-pin to a different version,
# grab the matching digest from:
#     https://nodejs.org/dist/v26.13.0/SHASUMS256.txt
# and update the constant below.
EXPECTED_SHA256 = None  # set to None to skip verification; set to hex string to enforce


def detect_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "win-arm64"
    return "win-x64"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_zip(version: str, arch: str) -> Path:
    filename = f"node-{version}-{arch}.zip"
    zip_path = TOOLS / filename
    TOOLS.mkdir(exist_ok=True)

    if zip_path.exists():
        size_mb = zip_path.stat().st_size / 1e6
        print(f"Found existing ZIP: {zip_path.name} ({size_mb:.1f} MB)")
        if size_mb < 20:
            print("  WARNING: file is smaller than expected (~35 MB). "
                  "It may be incomplete; delete and re-download if extraction fails.")
    else:
        url = f"https://nodejs.org/dist/{version}/{filename}"
        print(f"Downloading {url}")
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as exc:
            print(f"ERROR downloading: {exc}")
            print(f"\nManual fallback:")
            print(f"  1. Open in a browser: {url}")
            print(f"  2. Save the file to: {zip_path}")
            print(f"  3. Re-run this script.")
            raise SystemExit(1)
        print(f"Downloaded {zip_path.stat().st_size / 1e6:.1f} MB")

    if EXPECTED_SHA256:
        actual = sha256_of(zip_path)
        if actual != EXPECTED_SHA256:
            print(f"ERROR: SHA256 mismatch.")
            print(f"  expected: {EXPECTED_SHA256}")
            print(f"  actual:   {actual}")
            raise SystemExit(1)
        print(f"SHA256 verified.")
    else:
        print(f"SHA256: {sha256_of(zip_path)[:16]}…  (verification disabled)")

    return zip_path


def ensure_extracted(zip_path: Path, version: str, arch: str) -> Path:
    extract_dir = TOOLS / f"node-{version}-{arch}"
    if extract_dir.exists() and (extract_dir / "node.exe").exists():
        print(f"Already extracted: {extract_dir}")
        return extract_dir

    print(f"Extracting to {extract_dir} ...")
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(TOOLS)
    except zipfile.BadZipFile:
        print(f"ERROR: {zip_path} is not a valid ZIP. "
              "Delete it and re-run this script.")
        raise SystemExit(1)

    if not (extract_dir / "node.exe").exists():
        print(f"ERROR: node.exe missing after extraction.")
        print(f"  Expected at: {extract_dir / 'node.exe'}")
        print(f"  Contents of tools/: {[p.name for p in TOOLS.iterdir()]}")
        raise SystemExit(1)

    return extract_dir


def write_helper(node_dir: Path) -> None:
    helper = TOOLS / "use-node.ps1"
    helper.write_text(
        f'$env:PATH = "{node_dir};$env:PATH"\n'
        'Write-Host "Node.js PATH set for this PowerShell session." -ForegroundColor Green\n'
        'node --version\n'
        'npm --version\n',
        encoding="utf-8",
    )
    print(f"Wrote {helper.relative_to(ROOT)}")


def ensure_gitignore() -> None:
    gi = ROOT / ".gitignore"
    if not gi.exists():
        print("No .gitignore found; skipping.")
        return
    lines = gi.read_text(encoding="utf-8").splitlines()
    if "tools/" in lines:
        return
    gi.write_text(
        gi.read_text(encoding="utf-8").rstrip() + "\n\ntools/\n",
        encoding="utf-8",
    )
    print("Added tools/ to .gitignore")


def verify_node(node_dir: Path) -> tuple[str, str]:
    node_exe = node_dir / "node.exe"
    npm_cmd = node_dir / "npm.cmd"
    if not node_exe.exists() or not npm_cmd.exists():
        raise RuntimeError(f"Missing binaries in {node_dir}")

    node_ver = subprocess.run(
        [str(node_exe), "--version"],
        capture_output=True, text=True,
    )
    npm_ver = subprocess.run(
        f'"{npm_cmd}" --version',
        capture_output=True, text=True, shell=True,
    )

    if node_ver.returncode != 0:
        print(f"node --version failed:\n{node_ver.stderr}")
        raise RuntimeError("node.exe did not run")
    if npm_ver.returncode != 0:
        print(f"npm --version failed:\n{npm_ver.stderr}")
        raise RuntimeError("npm.cmd did not run")

    return node_ver.stdout.strip(), npm_ver.stdout.strip()


def run_frontend_build(node_dir: Path) -> int:
    env = os.environ.copy()
    env["PATH"] = str(node_dir) + os.pathsep + env.get("PATH", "")
    env["npm_config_yes"] = "true"
    env["npm_config_loglevel"] = "info"

    script = ROOT / "build_phase3a_frontend.py"
    if not script.exists():
        print(f"ERROR: {script} not found. Create it first (from the previous message).")
        return 1

    print("\nRunning build_phase3a_frontend.py with portable Node ...\n")
    return subprocess.run(
        [sys.executable, str(script)], env=env, cwd=ROOT
    ).returncode


def main() -> int:
    print(f"NyumbaLink portable Node {NODE_VERSION} -> {ROOT}\n")

    if not (ROOT / "manage.py").exists():
        print("ERROR: run this from the Django project root (where manage.py lives).")
        return 1

    arch = detect_arch()
    print(f"Target: Node {NODE_VERSION} ({arch})\n")

    try:
        zip_path = ensure_zip(NODE_VERSION, arch)
        node_dir = ensure_extracted(zip_path, NODE_VERSION, arch)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    write_helper(node_dir)
    ensure_gitignore()

    try:
        node_ver, npm_ver = verify_node(node_dir)
    except Exception as exc:
        print(f"ERROR verifying Node: {exc}")
        return 1

    print(f"\n  node --version -> {node_ver}")
    print(f"  npm  --version -> {npm_ver}\n")

    rc = run_frontend_build(node_dir)
    if rc != 0:
        print(f"\nFrontend build failed (exit {rc}). See output above.")
        return rc

    print(f"""
Done.

To use Node in future PowerShell sessions:

    . .\\tools\\use-node.ps1

Then start the dev server:

    Terminal 1:  .\\venv\\Scripts\\python.exe manage.py runserver
    Terminal 2:  . .\\tools\\use-node.ps1
                 cd frontend
                 npm run dev

Open http://localhost:5173
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())