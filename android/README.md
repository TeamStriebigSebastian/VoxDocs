# VoxDocs Voice Agent — Android

Hands-free voice assistant companion for VoxDocs.  
Say **"Hey VoxDocs"** to create notes, tasks, or hear open tasks — completely hands-free.

---

## Quick Start

### 1. Open in Android Studio

```bash
# Open the android/ folder as an Android Studio project
# Android Studio → File → Open → select android/
```

> **Gradle wrapper**: If the `gradle-wrapper.jar` is missing, Android Studio will
> auto-generate it. Alternatively run `gradle wrapper --gradle-version 8.5` from
> the `android/` directory.

### 2. Configure

After building and installing the APK on your device:

1. Open **VoxDocs Voice Agent**
2. Enter your **Server URL** (e.g. `http://192.168.1.100:8000`)
3. Enter your **Auth Token** (JWT from `/api/auth/login`)
4. Enable **Listening**
5. Tap **Disable Battery Optimization** to prevent Android from killing the service

### 3. Get an Auth Token

```bash
curl -X POST http://<server>:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# → copy the "access_token" value
```

### 4. Sideload APK

```bash
# Build debug APK
cd android/
./gradlew assembleDebug

# Install on connected device
adb install app/build/outputs/apk/debug/app-debug.apk
```

---

## User Stories

### Intent A — Create Note/Task (explicit case)

> **"Hey VoxDocs, für Demian, wir müssen die Medizin holen."**

- Detects case **Demian** (fuzzy match against local cache)
- Records audio → uploads to backend
- Backend transcribes with Whisper → creates entry + tasks
- Device plays confirmation: *"Gespeichert für Demian"*

### Intent B — Read Open Tasks

> **"Hey VoxDocs, zeig mir die offenen Aufgaben für Demian."**

- Detects **READ_TASKS** intent + case **Demian**
- Queries backend for open tasks
- Reads them aloud via TTS

### Intent C — Implicit Case (4-min context)

> **"Hey VoxDocs, wir müssen im Garten spielen."**

- No explicit case → uses **lastActiveCase** if < 4 minutes old
- Same flow as Intent A

---

## Architecture

```
┌───────────────────────────────────────────┐
│           VoiceListenerService            │
│  (Foreground Service — always running)    │
├───────────┬───────────┬───────────────────┤
│ Wakeword  │  Audio    │  SpeechRecognizer │
│ Engine    │  Recorder │  (intent parsing) │
├───────────┴───────────┴───────────────────┤
│            IntentParser                   │
│  (regex: CREATE vs READ, case extract)    │
├───────────────────────────────────────────┤
│ CaseMatcher  │  CaseRepository            │
│ (Levenshtein)│  (API cache + fuzzy)       │
├──────────────┴────────────────────────────┤
│         ApiClient (OkHttp)                │
│  POST /api/voice/intake                   │
│  GET  /api/voice/cases                    │
│  GET  /api/tasks/?case_uuid=X             │
├───────────────────────────────────────────┤
│ OfflineQueue  →  UploadWorker (WorkManager)│
├───────────────────────────────────────────┤
│        PlaybackController (TTS)           │
│  (German locale, headset routing)         │
└───────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `VoiceListenerService.kt` | Foreground service orchestrating the full lifecycle |
| `WakewordEngine.kt` | Interface for swappable wakeword engines |
| `SpeechRecognizerWakeword.kt` | MVP wakeword using Android SpeechRecognizer |
| `AudioRecorder.kt` | WAV recording with VAD silence detection |
| `IntentParser.kt` | Regex-based DE+EN intent classification |
| `CaseMatcher.kt` | Levenshtein fuzzy matching |
| `ApiClient.kt` | OkHttp backend client |
| `OfflineQueue.kt` + `UploadWorker.kt` | Offline retry with WorkManager |
| `PlaybackController.kt` | TTS with headset routing |

---

## Battery Optimization

Android aggressively kills background services. To keep VoxDocs Voice Agent running:

1. Open **Settings → Battery → Battery Optimization**
2. Find **VoxDocs Voice Agent** → set to **Not optimized**
3. Or use the in-app **"Disable Battery Optimization"** button

---

## Swapping the Wakeword Engine

The `WakewordEngine` interface allows plugging in any engine:

```kotlin
// In VoiceListenerService.onCreate():
// Default (SpeechRecognizer):
wakewordEngine = SpeechRecognizerWakeword(this)

// Porcupine (add dependency + API key):
// wakewordEngine = PorcupineWakewordEngine(this, "YOUR_API_KEY")
```

To implement Porcupine:
1. Add `ai.picovoice:porcupine-android:X.Y.Z` to `app/build.gradle.kts`
2. Create `PorcupineWakewordEngine` implementing `WakewordEngine`
3. Train a custom wakeword "Hey VoxDocs" in the Picovoice Console

---

## Backend API Endpoints

The Android app talks to these endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/voice/intake` | Upload audio + meta → transcribe & create entry |
| `GET`  | `/api/voice/cases` | Flat case list for local cache |
| `GET`  | `/api/tasks/?case_uuid=X` | Open tasks for a case |
| `POST` | `/api/auth/login` | Get JWT token |

---

## Permissions Required

- `RECORD_AUDIO` — microphone access
- `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MICROPHONE` — background listening
- `INTERNET` — API communication
- `POST_NOTIFICATIONS` — persistent notification (Android 13+)
- `BLUETOOTH_CONNECT` — headset audio routing
- `RECEIVE_BOOT_COMPLETED` — optional auto-start
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` — battery dialog
