# VoxDocs - Dental Speech-to-Text Documentation System

A GDPR-compliant speech recognition system for German dental practices that transcribes patient conversations during treatments and automatically classifies dental terminology.

## Features

- **Audio Recording PWA**: Progressive Web App with real-time waveform visualization
- **Speech-to-Text**: OpenAI Whisper Small (multilingual) for German dental terminology
- **Automatic Classification**: AI-based categorization of dental findings, diagnoses, treatments, and materials
- **Onboarding System**: 200-250 dental phrase training for voice adaptation
- **GDPR Compliant**: Complete on-premise deployment with AES-256 encryption
- **Multi-Room Support**: Handle multiple treatment rooms per practice
- **Export Integration**: JSON, CSV, XML export for practice management software

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (PWA)                           │
│  React + TypeScript + TailwindCSS + Vite                   │
│  - Audio recording with MediaRecorder API                   │
│  - Real-time waveform visualization                         │
│  - Offline-capable via Service Worker                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (API)                            │
│  FastAPI + SQLAlchemy + Whisper                            │
│  - Audio upload and encryption                              │
│  - Batch processing queue                                   │
│  - Transcription with dental vocabulary boost               │
│  - Rule-based classification                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
│  SQLite + Encrypted File Storage                           │
│  - AES-256-GCM file encryption                             │
│  - 90-day retention policy                                  │
│  - Secure deletion                                          │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for development)
- Python 3.11+ (for development)

### Production Deployment

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd VoxDocs
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with secure keys
   ```

3. Start services:
   ```bash
   docker-compose up -d
   ```

4. Access the application at `http://localhost:3000`

### Development Setup

1. Start development services:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. Or run services locally:

   **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Project Structure

```
VoxDocs/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry
│   └── requirements.txt
├── frontend/                # React PWA
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   ├── pages/          # Page components
│   │   ├── services/       # API client
│   │   └── stores/         # State management
│   └── package.json
├── docker/                  # Docker configuration
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── ml/                      # ML training scripts
├── docs/                    # Documentation
└── docker-compose.yml
```

## API Endpoints

### Audio
- `POST /api/audio/upload` - Upload audio recording
- `GET /api/audio/{uuid}` - Get recording details
- `GET /api/audio/` - List recordings
- `DELETE /api/audio/{uuid}` - Delete recording

### Transcription
- `GET /api/transcription/{uuid}` - Get transcription
- `POST /api/transcription/{uuid}/process` - Process recording
- `POST /api/transcription/{uuid}/correct` - Submit correction

### Classification
- `GET /api/classification/{uuid}` - Get classifications
- `POST /api/classification/classify-text` - Classify text

### Onboarding
- `POST /api/onboarding/start` - Start training session
- `GET /api/onboarding/{id}/phrases` - Get phrases to record
- `POST /api/onboarding/{id}/record` - Submit phrase recording

### Export
- `POST /api/export/generate` - Generate export file

## Dental Terminology Categories

The system recognizes and classifies the following categories:

| Category | German | Examples |
|----------|--------|----------|
| Tooth | Zahnbezeichnung | Zahn 16, Quadrant 2 |
| Surface | Fläche | mesial, distal, okklusal |
| Diagnosis | Diagnose | Karies Grad 2, Parodontitis |
| Finding | Befund | Taschentiefe 5mm, Lockerungsgrad 2 |
| Treatment | Behandlung | Wurzelkanalbehandlung, Extraktion |
| Material | Material | Composite, Zirkonoxid |
| Instrument | Instrument | Rosenbohrer, Kürette |
| Anatomy | Anatomie | Pulpa, Gingiva, Apex |

## Security & Privacy

- **Encryption**: AES-256-GCM for all audio files at rest
- **On-Premise**: No cloud dependencies, complete local deployment
- **Data Retention**: Automatic deletion after 90 days
- **Secure Delete**: Multi-pass overwrite for file deletion
- **Audit Logging**: All data access is logged

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT/session encryption key | (required) |
| `MASTER_KEY` | File encryption master key | (required) |
| `WHISPER_MODEL` | Whisper model size | `small` |
| `WHISPER_DEVICE` | Processing device | `cpu` |
| `BATCH_PROCESSING_HOUR` | Nightly processing hour | `2` |
| `RETENTION_DAYS` | Data retention period | `90` |

## Performance

- Audio processing: 30-60 seconds per minute of audio (CPU)
- Batch processing: Overnight for non-urgent recordings
- Immediate processing: Available for urgent cases

## License

Proprietary - All rights reserved

## Support

For support inquiries, please contact the development team.
