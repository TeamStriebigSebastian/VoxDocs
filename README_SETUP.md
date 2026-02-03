# VoxDocs Pflegedienst - Docker Setup & Test Guide

## 🏥 System Overview

**VoxDocs Pflegedienst** ist ein DSGVO-konformes Dokumentationssystem für Pflegedienste mit:

- ✅ **Multilingual**: Whisper transkribiert JEDE Sprache (Polnisch, Rumänisch, Türkisch, Arabisch, etc.)
- ✅ **Automatische Übersetzung**: LLM übersetzt alles ins Deutsche
- ✅ **Kategorisierung**: 4 Pflegekategorien (Zusammenfassung, Leistungen, Besonderheiten, Aufgaben)
- ✅ **TTS Vorlesen**: Thorsten (tiefe deutsche Männerstimme) liest die Doku vor
- ✅ **100% Lokal**: Keine externe API-Calls, alle Patientendaten bleiben lokal
- ✅ **PWA**: Progressive Web App mit Offline-Support, Kamera, Audio-Recorder

## 🔧 Voraussetzungen

- Docker & Docker Compose
- 8GB RAM minimum (16GB empfohlen)
- 20GB freier Speicher (für Modelle)
- Optional: NVIDIA GPU für schnellere Verarbeitung

## 🚀 Schnellstart

### 1. Repository klonen & Branch auschecken

```bash
git clone https://github.com/TeamStriebigSebastian/VoxDocs.git
cd VoxDocs
git checkout claude/nursing-care-appointments-gNlZ0
```

### 2. Environment-Datei erstellen

```bash
cp .env.example .env
```

**Wichtig**: Ändere die Passwörter in `.env`!

```bash
# Mindestens diese Werte ändern:
DB_PASSWORD=dein_sicheres_passwort
SECRET_KEY=ein-langer-zufälliger-string-min-32-zeichen
MASTER_KEY=genau-32-zeichen-für-encryption!!
```

### 3. Docker Container starten

```bash
# Alle Services bauen und starten
docker-compose up --build

# ODER im Hintergrund:
docker-compose up -d --build
```

**Was passiert jetzt:**
1. PostgreSQL wird gestartet
2. Ollama lädt das Mistral Modell herunter (~4GB, dauert beim ersten Mal!)
3. Backend installiert Whisper Medium Model (~1.5GB)
4. Piper lädt das Thorsten Voice Model (~20MB)
5. Frontend wird gebaut

**⏱️ Erster Start: 10-15 Minuten** (wegen Model-Downloads)

### 4. Modelle manuell herunterladen (optional, beschleunigt Start)

```bash
# Ollama Mistral Model vorher laden
docker-compose up -d ollama
docker exec -it voxdocs-ollama ollama pull mistral

# Dann Backend starten
docker-compose up backend frontend
```

## 🧪 System testen

### Schritt 1: Frontend öffnen

Browser öffnen: **http://localhost:3000**

Du solltest die VoxDocs PWA sehen.

### Schritt 2: Neuen Pflegetermin erstellen

1. Navigiere zu: **http://localhost:3000/nursing/appointment**
2. Optional: Patientenname eingeben (z.B. "Frau Müller")

### Schritt 3: Audio-Aufnahmen (Multilingual!)

Sprich in DEINER Sprache - das System übersetzt automatisch!

**Beispiel auf Polnisch:**
```
"Dzisiaj wykonałam poranną toaletę u pani Müller.
Ciśnienie krwi wynosiło 140 na 90.
Pacjentka była trochę niespokojana.
Proszę sprawdzić leki przy następnej wizycie."
```

**Beispiel auf Türkisch:**
```
"Bugün Frau Müller'in sabah bakımını yaptım.
Tansiyon 140'a 90'dı.
Hasta biraz huzursuzdu.
Bir sonraki ziyarette ilaçları kontrol edin."
```

**Beispiel auf Deutsch:**
```
"Habe heute bei Frau Müller die Morgenwäsche durchgeführt.
Blutdruck war 140 zu 90.
Patientin war etwas unruhig.
Bitte beim nächsten Mal Medikamente kontrollieren."
```

**💡 Das System:**
1. Whisper transkribiert in der Originalsprache
2. LLM (Ollama/Mistral) erkennt die Sprache
3. Übersetzt alles ins Deutsche
4. Kategorisiert in: Zusammenfassung, Leistungen, Besonderheiten, Aufgaben

### Schritt 4: Fotos aufnehmen

1. Klick auf "Kamera öffnen"
2. Nimm ein Testfoto auf (z.B. von deiner Hand 😄)
3. Du kannst mehrere Fotos machen

### Schritt 5: Termin abschließen

1. Klick auf "Termin abschließen" (unten)
2. **Backend verarbeitet jetzt:**
   - Whisper transkribiert alle Audio-Aufnahmen
   - LLM übersetzt und kategorisiert
   - Piper TTS generiert Audio mit Thorsten Stimme

### Schritt 6: Notification + Prüfen

- Nach ~30-60 Sekunden erscheint ein **Popup**: "Transkription fertig!"
- Klick auf **"Prüfen"** Button

### Schritt 7: Review-Seite

Du siehst jetzt:
- ✅ Zusammenfassung (auf Deutsch übersetzt!)
- ✅ Erbrachte Leistungen
- ✅ Besonderheiten
- ✅ Aufgaben für nächsten Termin
- 🔊 **"Abspielen"** Button → Thorsten liest die Doku vor!
- 📸 Foto-Galerie

### Schritt 8: Dokumentation bestätigen

1. Klick auf "Doku Bestätigen" (unten)
2. Namen eingeben (z.B. "Maria Schmidt")
3. Status wird auf "Bestätigt" gesetzt ✅

### Schritt 9: Übersicht

Gehe zu: **http://localhost:3000/appointments**

Siehst alle Termine mit Status-Badges!

## 🔍 Logs & Debugging

### Backend Logs anschauen

```bash
# Live logs
docker-compose logs -f backend

# Letzte 100 Zeilen
docker-compose logs --tail=100 backend
```

### Ollama Status prüfen

```bash
# Welche Modelle sind geladen?
docker exec -it voxdocs-ollama ollama list

# Mistral manuell testen
docker exec -it voxdocs-ollama ollama run mistral "Übersetze: Hello, how are you?"
```

### Datenbank prüfen

```bash
# In PostgreSQL einloggen
docker exec -it voxdocs-db psql -U voxdocs -d voxdocs

# Termine anzeigen
SELECT uuid, patient_name, status, started_at FROM appointments ORDER BY started_at DESC LIMIT 10;

# Transkriptionen anzeigen
SELECT id, summary, services FROM nursing_transcriptions LIMIT 5;
```

### WebSocket Verbindung testen

Browser Console (F12):
```javascript
const ws = new WebSocket('ws://localhost:3000/api/webhooks/ws');
ws.onmessage = (e) => console.log('Notification:', JSON.parse(e.data));
ws.send(JSON.stringify({type: 'ping'}));
```

## ⚡ Performance-Tipps

### 1. Kleineres Whisper Model für schnellere Tests

In `.env`:
```bash
WHISPER_MODEL=small  # Statt medium
```

### 2. GPU-Beschleunigung (NVIDIA)

In `docker-compose.yml` uncomment:
```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### 3. Modelle pre-cachen

```bash
# Alle Modelle vorher laden, dann starten
docker-compose up -d ollama
docker exec -it voxdocs-ollama ollama pull mistral

docker-compose up backend frontend
```

## 🛑 Probleme beheben

### "Ollama connection refused"

```bash
# Warte, bis Ollama ready ist
docker-compose logs ollama

# Sollte zeigen: "Ollama server started"
```

### "Transcription processing failed"

```bash
# Backend Logs checken
docker-compose logs backend | grep ERROR

# Häufig: Whisper Model noch nicht geladen
# Einfach warten und nochmal versuchen
```

### "Port already in use"

```bash
# Anderen Port in .env setzen
FRONTEND_PORT=8080

# Dann neu starten
docker-compose down
docker-compose up
```

### "Out of memory"

```bash
# Kleineres Whisper Model
WHISPER_MODEL=small

# Kleineres LLM Model
LLM_MODEL=llama3.2:7b  # Statt mistral
```

## 📊 API Dokumentation

Backend API: **http://localhost:8000/docs**

Wichtige Endpoints:
- `POST /api/appointments/create` - Neuer Termin
- `POST /api/appointments/{uuid}/upload-audio` - Audio hochladen
- `POST /api/appointments/{uuid}/upload-photo` - Foto hochladen
- `POST /api/appointments/{uuid}/complete` - Termin abschließen
- `GET /api/appointments/{uuid}` - Termin abrufen
- `POST /api/appointments/{uuid}/confirm` - Bestätigen
- `WS /api/webhooks/ws` - WebSocket Notifications

## 🗄️ Datenbank Schema

Wichtige Tabellen:
- `appointments` - Pflegetermine
- `audio_recordings` - Audio-Dateien
- `photos` - Fotos
- `nursing_transcriptions` - Verarbeitete Dokumentation mit Kategorien

## 🔐 Sicherheit

- ✅ Alle Audio/Foto-Dateien sind AES-256 verschlüsselt
- ✅ Keine externen API-Calls (DSGVO-konform)
- ✅ PostgreSQL mit Passwort-Schutz
- ✅ Verschlüsselte Netzwerkkommunikation zwischen Containern

## 📱 PWA Features

- ✅ Offline-Fähig
- ✅ Installierbar auf Smartphone/Tablet
- ✅ Native Kamera-Zugriff
- ✅ Native Audio-Recorder
- ✅ Push-Notifications

## 🎯 Workflow-Zusammenfassung

```
1. Pflegekraft erstellt Termin
   ↓
2. Spricht in BELIEBIGER Sprache (Polnisch, Türkisch, Deutsch, etc.)
   ↓
3. Macht Fotos von Befunden
   ↓
4. Schließt Termin ab
   ↓
5. Backend:
   - Whisper transkribiert (in Originalsprache)
   - Ollama LLM übersetzt nach Deutsch
   - Kategorisiert in 4 Pflegebereiche
   - Piper TTS generiert Audio (Thorsten Stimme)
   ↓
6. WebSocket Notification → Popup
   ↓
7. Pflegekraft klickt "Prüfen"
   ↓
8. Hört sich Doku an (TTS)
   ↓
9. Bestätigt mit Namen
   ↓
10. Fertig! ✅
```

## 🆘 Support

Bei Problemen:
1. Logs checken: `docker-compose logs backend`
2. GitHub Issues: https://github.com/TeamStriebigSebastian/VoxDocs/issues
3. Branch: `claude/nursing-care-appointments-gNlZ0`

---

**Entwickelt mit ❤️ für Pflegedienste** | DSGVO-konform | 100% Open Source
