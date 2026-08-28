# --- stage 1: build the React SPA ------------------------------------------
# Nothing used to build this, so frontend/dist was never in the image and the
# React UI was simply unreachable in a docker deployment.
FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# --- stage 2: the application ----------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_DEBUG=0 \
    MAX_UPLOAD_MB=200

# libgomp1 is required by scikit-learn (pulled in via markov_clustering).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code, then the SPA bundle from stage 1.
COPY . .
COPY --from=ui /ui/dist ./frontend/dist

# Runtime directories for uploads / generated results / cache / job blobs.
RUN mkdir -p uploads downloads cache output results

EXPOSE 8000

# Job state lives in SQLite (WAL) and heavy work runs in a separate process
# pool, so the API is no longer pinned to a single worker the way it was when
# jobs were kept in per-process dictionaries.
CMD ["gunicorn", "--workers", "4", "--threads", "4", "--timeout", "60", \
     "--bind", "0.0.0.0:8000", "app:app"]
