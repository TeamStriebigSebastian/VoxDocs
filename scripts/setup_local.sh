#!/bin/bash
# VoxDocs Local Development Setup
# Run this script to set up and test the system locally

set -e

echo "=========================================="
echo "VoxDocs Local Development Setup"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

echo "Python: $(python3 --version)"

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: ffmpeg is not installed (required for Whisper)"
    echo "Install with: apt install ffmpeg (Linux) or brew install ffmpeg (macOS)"
fi

# Create virtual environment
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/audio data/encrypted data/exports models logs

# Run tests
echo ""
echo "Running test suite..."
python scripts/test_whisper.py

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the backend server:"
echo "  source venv/bin/activate"
echo "  cd backend"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To start the frontend (in another terminal):"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"
echo ""
