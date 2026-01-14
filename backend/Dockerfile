# Backend Service
FROM python:3.11-slim

# Install system dependencies including build tools for PyAV
RUN apt-get update && apt-get install -y \
    # Audio/Video processing
    ffmpeg \
    libsndfile1 \
    # All FFmpeg development libraries for PyAV
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavdevice-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    # Build tools for PyAV
    build-essential \
    pkg-config \
    python3-dev \
    # Utilities
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS
RUN pip install piper-tts==1.2.0

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/encrypted storage/decrypted storage/tts logs

# Download Piper voice model (Thorsten - German male voice)
# Models will be downloaded at runtime if not present
RUN mkdir -p models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
