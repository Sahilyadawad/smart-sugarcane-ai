"""Vercel serverless entry point.

Vercel's Python runtime looks for a module-level ASGI application called ``app``.
This file puts ``backend/`` on the import path and re-exports the real FastAPI
application - all the logic stays in ``backend/app``.

If that import fails for any reason, we expose a tiny diagnostic app instead of
letting the exception escape. An uncaught import error on Vercel produces
``FUNCTION_INVOCATION_FAILED`` with no detail in the browser and nothing useful
without dashboard access, which makes remote debugging almost impossible. The
fallback below turns the same failure into a readable JSON traceback at any URL.

What is different on Vercel, and why it is fine:

* **No scikit-learn / pandas / SciPy.** The root ``requirements.txt`` installs a
  trimmed dependency set to stay under Vercel's 250 MB limit, so irrigation runs
  the documented water-balance rule engine instead of the trained Random Forest.
  The API reports ``model_source: rule_engine`` honestly.
* **No writable disk.** ``settings.persist_uploads`` detects ``VERCEL`` and stops
  saving uploaded photos. Analyses still run; only the thumbnail is missing.
* **A real database is required.** SQLite on a serverless filesystem is wiped
  between invocations, so ``DATABASE_URL`` must point at hosted Postgres.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.main import app
except Exception:  # noqa: BLE001 - must not let this escape, see module docstring
    _TRACEBACK = traceback.format_exc()
    _DIAGNOSTICS = {
        "error": "The backend failed to start.",
        "python_version": sys.version,
        "project_root": str(PROJECT_ROOT),
        "backend_dir_exists": BACKEND_DIR.is_dir(),
        "data_dir_exists": (PROJECT_ROOT / "data").is_dir(),
        "sys_path_head": sys.path[:4],
        "project_root_contents": sorted(p.name for p in PROJECT_ROOT.iterdir())
        if PROJECT_ROOT.is_dir()
        else [],
        "traceback": _TRACEBACK.splitlines(),
    }

    async def app(scope, receive, send):  # type: ignore[misc]
        """Minimal ASGI app that reports why the real one could not load."""
        if scope["type"] != "http":
            return
        import json

        body = json.dumps(_DIAGNOSTICS, indent=2, default=str).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


__all__ = ["app"]
