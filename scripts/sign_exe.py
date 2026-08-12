"""Authenticode-sign a built executable.

Two modes, selected by environment variable:

1. Real certificate (what actually removes the SmartScreen warning for everyone)
       set CHINESE_STUDY_CERT=C:\\path\\to\\certificate.pfx
       set CHINESE_STUDY_CERT_PASSWORD=...
2. Certificate already installed in the Windows certificate store
       set CHINESE_STUDY_CERT_SUBJECT="Your Company Name"

A timestamp server is always used so the signature stays valid after the
certificate expires.

This script cannot conjure trust: a self-signed certificate only silences the
warning on machines where that certificate has been installed as trusted. See
docs/WINDOWS_TRUST.md for the full picture.

Usage:  python scripts/sign_exe.py [path/to/ChineseStudy.exe]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = ROOT_DIR / "ChineseStudy.exe"

TIMESTAMP_URLS = (
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "http://timestamp.globalsign.com/tsa/r6advanced1",
)

SDK_GLOBS = (
    "C:/Program Files (x86)/Windows Kits/10/bin/*/x64/signtool.exe",
    "C:/Program Files (x86)/Windows Kits/10/bin/x64/signtool.exe",
    "C:/Program Files (x86)/Windows Kits/8.1/bin/x64/signtool.exe",
)


def find_signtool() -> str | None:
    """Locate signtool.exe on PATH or in an installed Windows SDK."""
    on_path = shutil.which("signtool")
    if on_path:
        return on_path
    for pattern in SDK_GLOBS:
        root = Path(pattern.split("*")[0])
        if not root.exists():
            continue
        matches = sorted(root.glob(pattern[len(str(root)) + 1 :]), reverse=True)
        if matches:
            return str(matches[0])
    return None


def _signtool_command(signtool: str, target: Path, timestamp_url: str) -> list[str] | None:
    command = [signtool, "sign", "/fd", "SHA256", "/tr", timestamp_url, "/td", "SHA256"]

    pfx_path = os.getenv("CHINESE_STUDY_CERT")
    subject = os.getenv("CHINESE_STUDY_CERT_SUBJECT")

    if pfx_path:
        if not Path(pfx_path).exists():
            raise SystemExit(f"Certificate file not found: {pfx_path}")
        command += ["/f", pfx_path]
        password = os.getenv("CHINESE_STUDY_CERT_PASSWORD")
        if password:
            command += ["/p", password]
    elif subject:
        command += ["/n", subject, "/a"]
    else:
        return None

    command.append(str(target))
    return command


def sign_with_powershell(target: Path) -> bool:
    """Fallback for machines with no Windows SDK, using the certificate store."""
    subject = os.getenv("CHINESE_STUDY_CERT_SUBJECT")
    if not subject:
        return False
    script = (
        f"$cert = Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | "
        f"Where-Object {{ $_.Subject -like '*{subject}*' }} | Select-Object -First 1; "
        f"if (-not $cert) {{ Write-Error 'No matching code-signing certificate'; exit 1 }}; "
        f"Set-AuthenticodeSignature -FilePath '{target}' -Certificate $cert "
        f"-TimestampServer '{TIMESTAMP_URLS[0]}' -HashAlgorithm SHA256"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip() or result.stderr.strip())
    return result.returncode == 0


def sign(target: Path = DEFAULT_TARGET) -> bool:
    """Sign ``target`` in place. Returns True when a signature was applied."""
    if not target.exists():
        raise SystemExit(f"Nothing to sign: {target} does not exist.")

    if not os.getenv("CHINESE_STUDY_CERT") and not os.getenv("CHINESE_STUDY_CERT_SUBJECT"):
        print(
            "No signing certificate configured -- skipping.\n"
            "  Set CHINESE_STUDY_CERT (.pfx file) or CHINESE_STUDY_CERT_SUBJECT\n"
            "  (certificate already in the Windows store). See docs/WINDOWS_TRUST.md."
        )
        return False

    signtool = find_signtool()
    if signtool is None:
        print("signtool.exe not found; falling back to PowerShell signing.")
        return sign_with_powershell(target)

    # Timestamp servers go down; try each before giving up.
    for timestamp_url in TIMESTAMP_URLS:
        command = _signtool_command(signtool, target, timestamp_url)
        if command is None:
            return False
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Signed {target.name} (timestamp: {timestamp_url})")
            return True
        print(f"  signing via {timestamp_url} failed: {result.stderr.strip() or result.stdout.strip()}")

    raise SystemExit("Signing failed with every timestamp server.")


def verify(target: Path = DEFAULT_TARGET) -> None:
    """Print the current signature status of the executable."""
    signtool = find_signtool()
    if signtool is None:
        print("signtool.exe not available; cannot verify.")
        return
    result = subprocess.run(
        [signtool, "verify", "/pa", "/v", str(target)], capture_output=True, text=True
    )
    print(result.stdout.strip() or result.stderr.strip())


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    if sign(path):
        verify(path)
