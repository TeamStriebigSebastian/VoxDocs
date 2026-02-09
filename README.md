# VoxDocs -  Speech-to-Text Documentation System

A local-first, privacy-focused speech documentation system for multilingual teams. It allows users to speak in their native language, automatically translates to the team's language, tracks tasks from voice reports, and securely attaches photos.
Designed for teams where members speak different languages but need to collaborate seamlessly. No uploading of sensitive data to the cloud.
Over the MCP Server integration, it enables AI Agents to ask specific questions towards the documentation. Finding the needle in the haystack!

## Features

- **Audio Recording PWA**: Progressive Web App with real-time waveform visualization
- **Speech-to-Text**: OpenAI Whisper Small (multilingual) for general purpose dictation
- **Automatic Classification**: AI-based categorization of tasks, notes, and updates (identifying custom categories)
- **Multilingual Support**: Speak in ANY language, get documentation in your configured language
- **GDPR Compliant**: Complete on-premise deployment with AES-256 encryption
- **Multi-Group Support**: Configure different groups, with different categories, down to the classification prompt
- **Export Integration**: Zip (CSV + photos) export for creating reports, like billing

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
│  - Transcription with vocabulary boost                      │
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



### Export
- `POST /api/export/generate` - Generate export file

## Categories

The system automatically classifies your voice notes into categories. These can be customized, but default to:

| Category | Description | Example |
|----------|-------------|---------|
| Task | Action items | "Order printer paper", "Call client X" |
| Update | Status reports | "Project A is 50% complete" |
| Note | General observations | "Meeting room needs cleaning" |
| Issue | Problems encountered | "Server X is down" |

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

MIT License - see [LICENSE](LICENSE) for details

## Support

For support inquiries, please contact the development team.
