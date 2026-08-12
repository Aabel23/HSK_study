"""Gunicorn picks this up automatically from the working directory (its
``--config`` default is ``./gunicorn.conf.py``), so it applies even though
the Render Start Command is just ``gunicorn hsk_study.wsgi`` with no flags.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
