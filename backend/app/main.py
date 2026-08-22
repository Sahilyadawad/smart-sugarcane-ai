"""Smart Sugarcane AI - FastAPI application entry point.

Run from the backend/ directory:

    uvicorn app.main:app --reload

Interactive API docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.core.config import settings
from app.database import init_db
from app.ml import disease_model, irrigation_model, soil_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("smart_sugarcane")


#: Set when the database could not be initialised, so /api/system/status can
#: report the reason instead of the app simply failing.
DB_INIT_ERROR: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global DB_INIT_ERROR
    try:
        init_db()
        logger.info("Database ready at %s", settings.database_uri)
    except Exception as exc:  # noqa: BLE001
        # A failure here must not kill the whole process. On serverless that
        # turns every single route - including the health check - into an
        # opaque FUNCTION_INVOCATION_FAILED, which hides the actual cause.
        # Better to boot, serve the diagnostics endpoints, and say what broke.
        DB_INIT_ERROR = f"{type(exc).__name__}: {exc}"
        logger.error("DATABASE INITIALISATION FAILED: %s", DB_INIT_ERROR)
        logger.error("URI attempted: %s", settings.database_uri)
        logger.error(
            "Endpoints that need the database will return errors. On a serverless host "
            "set DATABASE_URL to a hosted Postgres connection string."
        )

    irrigation_status = irrigation_model.status()
    disease_status = disease_model.status()
    soil_status = soil_model.status()

    logger.info("=" * 78)
    logger.info("%s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Model mode: %s", settings.MODEL_MODE)
    logger.info(
        "  Irrigation : %s",
        "TRAINED MODEL" if irrigation_status["trained_model_available"] else "RULE ENGINE (no model file)",
    )
    logger.info(
        "  Disease    : %s",
        "TRAINED MODEL" if disease_status["trained_model_available"] else "DEMO HEURISTIC (no model file)",
    )
    logger.info(
        "  Soil       : %s",
        "TRAINED MODEL" if soil_status["trained_model_available"] else "DEMO HEURISTIC (no model file)",
    )
    logger.info("Uploads    : %s", settings.upload_path)
    logger.info("Docs       : http://localhost:8000/docs")
    logger.info("=" * 78)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered sugarcane irrigation, disease detection, soil analysis and fertilizer "
        "recommendation API.\n\n"
        "**Honesty policy:** every AI response carries a `model_source` field. "
        "`trained_model` means a real trained model produced it. `rule_engine` means a documented "
        "water-balance calculation produced it. `demo_heuristic` means a transparent colour and "
        "texture estimate produced it, which is illustrative only and must never be used as a "
        "diagnosis. Check `GET /api/system/status` at any time."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded images are served straight from disk at /uploads/... - but only where
# there is a writable disk. On serverless the mount would fail at import time.
if settings.persist_uploads:
    try:
        settings.upload_path.mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")
    except OSError as exc:  # pragma: no cover - platform dependent
        logger.warning("Uploads directory is not writable (%s). Image storage disabled.", exc)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn pydantic errors into a message a farmer-facing UI can display."""
    problems = []
    for error in exc.errors():
        location = " -> ".join(str(part) for part in error.get("loc", []) if part != "body")
        problems.append(f"{location or 'input'}: {error.get('msg', 'invalid value')}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Some of the values sent were not valid.",
            "problems": problems,
        },
    )


# ---------------------------------------------------------------------------
# Single-server mode
# ---------------------------------------------------------------------------
# If the frontend has been built (`cd frontend && npm run build`), serve it from
# this same process. That gives one origin for the whole application, which
# means no CORS configuration, one port to expose, and a deployment that matches
# the single-project Vercel setup.
#
# Mounted LAST so that /api, /uploads, /docs and / above always win. Anything
# else falls through to index.html, which is what a client-side router needs.
FRONTEND_DIST = settings.project_root / "frontend" / "dist"


class SpaStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for unknown paths.

    React Router owns routes like /irrigation and /soil-analysis. They exist
    only in the browser, so a direct visit or a refresh asks the server for a
    file that was never built. Plain StaticFiles answers 404; a single-page app
    needs index.html returned instead so the router can take over.

    Real missing assets (a .js or .png that is genuinely absent) still 404,
    because returning HTML for those would hide the actual problem.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not Path(path).suffix:
                return await super().get_response("index.html", scope)
            raise


if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
    # The website owns "/". No JSON root route here, or it would shadow the app.
    app.mount("/", SpaStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logger.info("Serving the built frontend from %s", FRONTEND_DIST)
else:
    logger.info(
        "No frontend build found at %s - API only. Run 'npm run build' in frontend/ "
        "to serve the site from this server too.",
        FRONTEND_DIST,
    )

    @app.get("/", tags=["System"])
    def root() -> dict:
        """API-only landing response, used when no frontend build is present."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": settings.API_PREFIX,
            "status": f"{settings.API_PREFIX}/system/status",
            "message": "Smart Sugarcane AI backend is running (API only).",
        }
