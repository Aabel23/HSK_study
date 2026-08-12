"""Internal entry point used to package and run Chinese Study."""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if not getattr(sys, "frozen", False) and str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

APP_HOST = "127.0.0.1"
APP_PORT = int(os.getenv("CHINESE_STUDY_PORT", "8000"))
APP_URL = f"http://{APP_HOST}:{APP_PORT}"


def open_browser() -> None:
    try:
        webbrowser.open(APP_URL)
    except webbrowser.Error:
        pass


def main() -> None:
    import uvicorn

    from backend.main import app

    if os.getenv("CHINESE_STUDY_NO_BROWSER") != "1":
        threading.Timer(1.5, open_browser).start()
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, reload=False)


if __name__ == "__main__":
    main()
