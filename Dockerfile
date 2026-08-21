# Smart Sugarcane AI - backend container
#
# Build from the PROJECT ROOT, not from backend/:
#     docker build -t smart-sugarcane-api .
#     docker run -p 8000:8000 --env-file backend/.env smart-sugarcane-api
#
# The whole project layout is preserved inside the image because
# app/core/config.py derives every path from PROJECT_ROOT (three levels above
# itself). The backend reads data/ and models/ from the project root, so
# flattening the tree would break both.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries. libgomp1 is required by scikit-learn's OpenMP code, and
# libglib2.0-0 by opencv. Installed before the app layer so they stay cached.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, so code changes do not invalidate the pip layer.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# Application code and the runtime knowledge base / models.
COPY backend/ ./backend/
COPY data/ ./data/
COPY ml/ ./ml/
COPY models/ ./models/

# models/*.joblib is gitignored, so a clone of this repo has no trained model and
# the API would silently fall back to the rule engine in production. Training
# during the build takes ~30 s and keeps the deployed behaviour identical to
# local. Set --build-arg TRAIN_IRRIGATION_MODEL=0 to skip it.
ARG TRAIN_IRRIGATION_MODEL=1
RUN if [ "$TRAIN_IRRIGATION_MODEL" = "1" ] && [ ! -f models/irrigation_model.joblib ]; then \
        echo "No trained model in the build context - training one now..." && \
        python ml/irrigation/train.py --rows 8000 ; \
    else \
        echo "Using the model already present in models/ (or training disabled)." ; \
    fi

# Upload target. On most PaaS free tiers this is ephemeral - mount a volume or
# point UPLOAD_DIR at object storage if uploads must survive a redeploy.
RUN mkdir -p /app/uploads/plants /app/uploads/soil

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-8000}/api/system/health || exit 1

# Most hosts inject $PORT. Bind 0.0.0.0 so the platform's proxy can reach us,
# and use the shell form so ${PORT} is expanded at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
