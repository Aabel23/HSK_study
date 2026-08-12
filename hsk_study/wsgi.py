"""Entry point matching the Render service's existing Start Command
(``gunicorn hsk_study.wsgi``) so the deploy works without a dashboard change.

``backend.main:app`` is an ASGI app; ``gunicorn.conf.py`` at the repo root
sets ``worker_class`` to the uvicorn worker so gunicorn speaks ASGI to it
instead of assuming plain WSGI.
"""

from __future__ import annotations

from backend.main import app as application

__all__ = ["application"]
