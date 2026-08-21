"""Vercel serverless entry point.

Vercel's Python runtime looks for a module-level ASGI application called ``app``.
This file only puts ``backend/`` on the import path and re-exports the real
FastAPI application - all the logic stays in ``backend/app``.

The project layout is preserved on Vercel (the whole repository is available to
the function), so ``app/core/config.py`` still resolves PROJECT_ROOT correctly
and finds ``data/`` for the knowledge base.

What is different on Vercel, and why it is fine:

* **No scikit-learn / pandas / SciPy.** The root ``requirements.txt`` installs a
  trimmed dependency set to stay under Vercel's 250 MB limit, so the irrigation
  module runs the documented water-balance rule engine instead of the trained
  Random Forest. That is the same physics the forest was trained to reproduce
  (R2 0.96 against it), and the API reports ``model_source: rule_engine``
  honestly.
* **No writable disk.** ``settings.persist_uploads`` detects the ``VERCEL``
  environment variable and stops trying to save uploaded photos. Analyses are
  still computed and stored; only the thumbnail is missing.
* **A real database is required.** SQLite on a serverless filesystem would be
  wiped between invocations, so ``DATABASE_URL`` must point at hosted Postgres.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402  (path setup must run first)

__all__ = ["app"]
