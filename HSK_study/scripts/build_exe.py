"""Build ChineseStudy.exe directly in the project root.

The defaults here are chosen to make the produced binary look and behave like a
real Windows application rather than an anonymous blob:

* an embedded VERSIONINFO resource and an application icon, so Explorer,
  SmartScreen and UAC show a product name and publisher instead of blanks;
* UPX compression disabled, because packed executables are one of the most
  common causes of false-positive antivirus detections;
* an optional Authenticode signature applied straight after the build.

Only a certificate from a trusted CA removes the SmartScreen "unknown
publisher" warning outright -- see docs/WINDOWS_TRUST.md.

Usage:
    python scripts/build_exe.py                 # one-file console build
    python scripts/build_exe.py --windowed      # no console window
    python scripts/build_exe.py --onedir        # folder build (starts faster)
    python scripts/build_exe.py --sign          # sign using the env config
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import version_info  # noqa: E402  (needs the path fix above)

BUILD_DIR = ROOT_DIR / "build"
ENTRY_FILE = ROOT_DIR / "scripts" / "app_entry.py"
ICON_FILE = ROOT_DIR / "assets" / "app_icon.ico"
OUTPUT_FILE = ROOT_DIR / "ChineseStudy.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ChineseStudy executable.")
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Hide the console window (logs still go to %%LOCALAPPDATA%%\\ChineseStudy\\logs).",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Produce a folder instead of a single file. Starts faster and trips fewer AV heuristics.",
    )
    parser.add_argument(
        "--upx",
        action="store_true",
        help="Re-enable UPX compression. Smaller output, but a frequent antivirus false positive.",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Run scripts/sign_exe.py on the result.",
    )
    return parser.parse_args()


def ensure_icon() -> Path | None:
    if ICON_FILE.exists():
        return ICON_FILE
    print("Icon missing, generating it...")
    try:
        from scripts import make_icon

        make_icon.main()
    except Exception as error:  # pragma: no cover - optional dependency
        print(f"  could not generate the icon ({error}); building without one.")
        return None
    return ICON_FILE if ICON_FILE.exists() else None


def main() -> None:
    args = parse_args()

    try:
        import PyInstaller.__main__
    except ImportError as error:
        raise SystemExit(
            "PyInstaller is not installed. Run: "
            "python -m pip install -r scripts/requirements-build.txt"
        ) from error

    web_dist = ROOT_DIR / "frontend-web" / "dist"
    if not web_dist.exists():
        raise SystemExit(
            "frontend-web/dist is missing. Run 'npm run build' in frontend-web/ first."
        )

    version_file = version_info.write()
    print(f"Version resource: {version_file}")

    options = [
        str(ENTRY_FILE),
        "--name=ChineseStudy",
        "--onedir" if args.onedir else "--onefile",
        "--windowed" if args.windowed else "--console",
        "--clean",
        "--noconfirm",
        f"--paths={ROOT_DIR}",
        f"--version-file={version_file}",
        f"--add-data={ROOT_DIR / 'frontend'}{os.pathsep}frontend",
        f"--add-data={web_dist}{os.pathsep}frontend-web/dist",
        # The HSK 1-9 dataset. Without this the packaged app only seeds the 150
        # curated HSK1 words instead of the full ~11k vocabulary.
        f"--add-data={ROOT_DIR / 'scripts' / 'data'}{os.pathsep}scripts/data",
        f"--distpath={ROOT_DIR}",
        f"--workpath={BUILD_DIR / 'pyinstaller'}",
        f"--specpath={BUILD_DIR}",
    ]

    icon = ensure_icon()
    if icon is not None:
        options.append(f"--icon={icon}")

    if not args.upx:
        # UPX-packed binaries are disproportionately flagged by antivirus
        # engines; the extra megabytes are worth avoiding that.
        options.append("--noupx")

    PyInstaller.__main__.run(options)

    target = OUTPUT_FILE if not args.onedir else ROOT_DIR / "ChineseStudy" / "ChineseStudy.exe"
    if not target.exists():
        raise SystemExit(f"Build finished but {target} was not produced.")
    print(f"Built executable: {target} ({target.stat().st_size / 1_048_576:.1f} MB)")

    if args.sign:
        from scripts import sign_exe

        sign_exe.sign(target)
    elif shutil.which("signtool") or os.getenv("CHINESE_STUDY_CERT"):
        print("Tip: run 'python scripts/sign_exe.py' to Authenticode-sign this build.")


if __name__ == "__main__":
    main()
