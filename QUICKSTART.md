# VoxDocs - Schnellstart

## Voraussetzungen

- Docker Desktop (Windows/Mac) oder Docker Engine (Linux)
- Docker Compose
- Ca. 4GB freier Speicher (für Whisper Model)

## 1. Repository klonen

```bash
git clone <repository-url>
cd VoxDocs
```

## 2. System starten

```bash
docker-compose -f docker-compose.test.yml up --build
```

**Hinweis:** Der erste Start dauert 5-10 Minuten, da das Whisper-Modell heruntergeladen wird.

## 3. Testen

Öffne im Browser: **http://localhost:3000**

### Audio aufnehmen:
1. Behandlungsraum auswählen
2. Auf den großen blauen Mikrofon-Button klicken
3. Sprechen (z.B. "Zahn eins sechs mesial Karies Grad zwei")
4. Erneut klicken zum Stoppen

### Transkription ansehen:
1. Unter "Aufnahmen" die Aufnahme auswählen
2. Auf "Transkription ansehen" klicken

## API direkt testen

### Health Check:
```bash
curl http://localhost:8000/api/health
```

### Audio hochladen und sofort verarbeiten:
```bash
curl -X POST "http://localhost:8000/api/audio/upload" \
  -F "file=@test.wav" \
  -F "practice_id=1" \
  -F "process_immediately=true"
```

### Text klassifizieren (ohne Audio):
```bash
curl -X POST "http://localhost:8000/api/classification/classify-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Zahn 16 mesial Karies Grad 2"}'
```

## System stoppen

```bash
docker-compose -f docker-compose.test.yml down
```

## Logs ansehen

```bash
docker logs voxdocs-backend -f
```

## Troubleshooting

### Container startet nicht:
```bash
docker-compose -f docker-compose.test.yml logs backend
```

### Whisper-Model wird nicht gefunden:
Das Model wird beim ersten Build heruntergeladen. Bei Problemen:
```bash
docker-compose -f docker-compose.test.yml build --no-cache backend
```

### Port bereits belegt:
Ports in `docker-compose.test.yml` anpassen:
- Backend: 8000
- Frontend: 3000
