# Backend Service (FastAPI)
#
# Multi-stage build:
# - builder: compiles/installs Python deps needing native extensions (e.g., PyAV)
# - runtime: minimal OS deps + prebuilt wheels

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /wheels

# Build dependencies for native Python packages (e.g., PyAV) and ffmpeg headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    python3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels for all dependencies so the runtime image doesn't need compilers/headers.
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt && \
    pip wheel --no-cache-dir --wheel-dir /wheels piper-tts==1.2.0

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime-only OS dependencies:
# - ffmpeg provides libav* shared libs required by PyAV at runtime
# - libsndfile1 used by soundfile/librosa
# - curl used for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    pip install --no-cache-dir --no-index --find-links=/wheels piper-tts==1.2.0 && \
    rm -rf /wheels

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/encrypted storage/decrypted storage/tts logs models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
