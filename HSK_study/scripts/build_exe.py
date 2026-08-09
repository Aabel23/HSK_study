"""Build ChineseStudy.exe directly in the project root."""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT_DIR / "build"
ENTRY_FILE = ROOT_DIR / "scripts" / "app_entry.py"
OUTPUT_FILE = ROOT_DIR / "ChineseStudy.exe"


def main() -> None:
    try:
        import PyInstaller.__main__
    except ImportError as error:
        raise SystemExit(
            "PyInstaller is not installed. Run: "
            "python -m pip install -r scripts/requirements-build.txt"
        ) from error

    PyInstaller.__main__.run(
        [
            str(ENTRY_FILE),
            "--name=ChineseStudy",
            "--onefile",
            "--console",
            "--clean",
            "--noconfirm",
            f"--paths={ROOT_DIR}",
            f"--add-data={ROOT_DIR / 'frontend'}{os.pathsep}frontend",
            f"--distpath={ROOT_DIR}",
            f"--workpath={BUILD_DIR / 'pyinstaller'}",
            f"--specpath={BUILD_DIR}",
        ]
    )
    print(f"Built executable: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
