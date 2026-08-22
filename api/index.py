"""Vercel serverless entry point.

Vercel's Python builder scans this file **statically** for a module-level
``app``, ``application`` or ``handler``. That name therefore has to be a plain
top-level assignment - putting the import inside a ``try`` block hides it from
the scanner and the build fails with:

    Could not find a top-level "app", "application", or "handler"

Hence the factory below: the error handling lives inside ``_create_app()`` and
the module still ends with a bare ``app = _create_app()``.

Why the error handling exists at all: an uncaught import error on Vercel yields
``FUNCTION_INVOCATION_FAILED`` with no detail in the browser, which is nearly
impossible to debug without dashboard access. On failure we serve a tiny ASGI
app that returns the traceback and environment facts as JSON instead.

What differs on Vercel, and why it is acceptable:

* **No scikit-learn / pandas / SciPy.** The root ``requirements.txt`` installs a
  trimmed set to stay under Vercel's 250 MB function limit, so irrigation uses
  the documented water-balance rule engine rather than the trained Random
  Forest. The API reports ``model_source: rule_engine`` honestly.
* **No writable disk.** ``settings.persist_uploads`` detects ``VERCEL`` and skips
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


def _diagnostic_app(error_traceback: str):
    """A minimal ASGI app that explains why the real application did not load."""
    details = {
        "error": "The Smart Sugarcane AI backend failed to start.",
        "python_version": sys.version,
        "project_root": str(PROJECT_ROOT),
        "backend_dir_exists": BACKEND_DIR.is_dir(),
        "data_dir_exists": (PROJECT_ROOT / "data").is_dir(),
        "sys_path_head": sys.path[:4],
        "project_root_contents": sorted(p.name for p in PROJECT_ROOT.iterdir())
        if PROJECT_ROOT.is_dir()
        else [],
        "traceback": error_traceback.splitlines(),
    }

    async def diagnostic(scope, receive, send):
        if scope["type"] != "http":
            return
        import json

        body = json.dumps(details, indent=2, default=str).encode()
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

    return diagnostic


def _create_app():
    try:
        from app.main import app as fastapi_app

        return fastapi_app
    except Exception:  # noqa: BLE001 - see module docstring
        return _diagnostic_app(traceback.format_exc())


app = _create_app()

__all__ = ["app"]
