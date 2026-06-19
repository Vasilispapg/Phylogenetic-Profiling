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

# Application code.
COPY . .

# Runtime directories for uploads / generated results / cache.
RUN mkdir -p uploads downloads cache output

EXPOSE 8000

# A single worker keeps the in-memory job store consistent across requests
# (status polling + downloads), while threads serve concurrent uploads/polls.
# Background tree construction runs in-process inside this worker.
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--timeout", "120", \
     "--bind", "0.0.0.0:8000", "app:app"]
