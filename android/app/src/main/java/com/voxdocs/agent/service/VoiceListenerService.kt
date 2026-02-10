package com.voxdocs.agent.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.media.AudioManager
import android.os.Bundle
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import androidx.core.app.NotificationCompat
import com.voxdocs.agent.MainActivity
import com.voxdocs.agent.R
import com.voxdocs.agent.VoxDocsApp
import com.voxdocs.agent.api.*
import com.voxdocs.agent.audio.AudioRecorder
import com.voxdocs.agent.data.CaseRepository
import com.voxdocs.agent.data.OfflineQueue
import com.voxdocs.agent.data.SettingsStore
import com.voxdocs.agent.intent.IntentParser
import com.voxdocs.agent.tts.PlaybackController
import com.voxdocs.agent.wakeword.SpeechRecognizerWakeword
import com.voxdocs.agent.wakeword.WakewordEngine
import com.voxdocs.agent.worker.UploadWorker
import kotlinx.coroutines.*
import java.io.File
import java.time.Instant
import java.time.format.DateTimeFormatter

/**
 * The core foreground service that orchestrates the entire voice assistant lifecycle:
 *
 *   IDLE → (wakeword) → RECORDING → (silence/timeout) → PROCESSING → IDLE
 *
 * Components managed:
 *  - [WakewordEngine] for trigger detection
 *  - [AudioRecorder] for command capture
 *  - [SpeechRecognizer] for parallel intent transcript
 *  - [IntentParser] for intent classification
 *  - [ApiClient] for backend communication
 *  - [PlaybackController] for TTS feedback
 *  - [OfflineQueue] for failed upload retry
 */
class VoiceListenerService : Service(), WakewordEngine.WakewordListener {

    // ── State ───────────────────────────────────────────────────────

    private enum class State { IDLE, RECORDING, PROCESSING }
    @Volatile private var state = State.IDLE

    // ── Dependencies ────────────────────────────────────────────────

    private lateinit var settings: SettingsStore
    private lateinit var wakewordEngine: WakewordEngine
    private lateinit var recorder: AudioRecorder
    private lateinit var apiClient: ApiClient
    private lateinit var caseRepo: CaseRepository
    private lateinit var offlineQueue: OfflineQueue
    private lateinit var playback: PlaybackController

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    // SpeechRecognizer for command transcript (runs alongside AudioRecorder)
    private var commandRecognizer: SpeechRecognizer? = null
    private var commandTranscript: String = ""

    // ── Service lifecycle ───────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        settings = VoxDocsApp.instance.settings
        recorder = AudioRecorder()
        apiClient = ApiClient(settings)
        caseRepo = CaseRepository(this, apiClient, settings)
        offlineQueue = OfflineQueue(this)
        playback = PlaybackController(this)

        // The wakeword engine can be swapped here.
        // To use Porcupine: wakewordEngine = PorcupineWakewordEngine(this, apiKey)
        wakewordEngine = SpeechRecognizerWakeword(this)

        caseRepo.loadFromCache()

        serviceScope.launch {
            playback.init()
            caseRepo.refreshIfNeeded()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, buildNotification("Listening for \"Hey VoxDocs\"…"))
        startWakewordListening()
        return START_STICKY
    }

    override fun onDestroy() {
        state = State.IDLE
        wakewordEngine.stop()
        recorder.stop()
        commandRecognizer?.cancel()
        commandRecognizer?.destroy()
        playback.shutdown()
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── Wakeword callbacks ──────────────────────────────────────────

    override fun onWakewordDetected() {
        Log.i(TAG, "⚡ Wakeword detected!")
        if (state != State.IDLE) {
            Log.w(TAG, "Already in state $state, ignoring wakeword")
            startWakewordListening()
            return
        }
        serviceScope.launch { handleWakeword() }
    }

    override fun onError(message: String) {
        Log.w(TAG, "Wakeword engine error: $message")
    }

    // ── Main flow ───────────────────────────────────────────────────

    private suspend fun handleWakeword() {
        state = State.RECORDING
        updateNotification("🔴 Recording command…")

        // Play beep to signal recording start
        playback.playBeep()
        delay(300) // small gap after beep

        // Start parallel SpeechRecognizer for intent parsing
        commandTranscript = ""
        startCommandRecognizer()

        // Record audio to WAV file
        val audioFile = File(filesDir, "cmd_${System.currentTimeMillis()}.wav")
        try {
            recorder.record(audioFile)
        } catch (e: Exception) {
            Log.e(TAG, "Recording failed", e)
            state = State.IDLE
            startWakewordListening()
            return
        }

        // Stop the command recognizer
        stopCommandRecognizer()

        // Process the command
        state = State.PROCESSING
        updateNotification("⏳ Processing…")

        processCommand(audioFile, commandTranscript)

        // Return to idle
        state = State.IDLE
        updateNotification("Listening for \"Hey VoxDocs\"…")
        startWakewordListening()
    }

    private suspend fun processCommand(audioFile: File, transcript: String) {
        Log.i(TAG, "Processing command. Transcript: \"$transcript\"")

        // 1. Parse intent from local transcript
        val intent = IntentParser.parse(transcript)

        // 2. Resolve case
        val resolvedCase = resolveCase(intent.caseName)
        if (resolvedCase == null) {
            playback.speak("Ich konnte keinen passenden Fall finden. Bitte versuche es erneut.")
            audioFile.delete()
            return
        }

        // Update last active case
        settings.touchLastActiveCase(resolvedCase.id, resolvedCase.name)

        // 3. Execute based on intent type
        when (intent.type) {
            VoiceIntentType.READ_OPEN_TASKS -> handleReadTasks(resolvedCase, audioFile)
            VoiceIntentType.CREATE_TASK_OR_NOTE,
            VoiceIntentType.UNKNOWN -> handleCreate(resolvedCase, audioFile)
        }
    }

    // ── Intent handlers ─────────────────────────────────────────────

    private suspend fun handleCreate(case: CaseInfo, audioFile: File) {
        val isHeadset = isHeadsetConnected()
        val meta = IntakeMeta(
            deviceId = settings.deviceId,
            locale = "de-DE",
            capturedAt = DateTimeFormatter.ISO_INSTANT.format(Instant.now()),
            caseName = case.name,
            caseId = case.id,
            intent = "CREATE",
            source = if (isHeadset) "headset" else "phone",
            clientVersion = "0.1.0",
        )

        try {
            val response = apiClient.uploadVoiceCommand(audioFile, meta)
            playback.playBeep()
            playback.speakConfirmation(case.name, response.createdTasks.size)
            audioFile.delete()
            Log.i(TAG, "Upload successful for case ${case.name}")
        } catch (e: Exception) {
            Log.e(TAG, "Upload failed, queueing offline", e)
            offlineQueue.enqueue(audioFile, meta.toJson())
            UploadWorker.enqueue(this)
            playback.speak("Verbindung fehlgeschlagen. Die Aufnahme wird später gesendet.")
            audioFile.delete()
        }
    }

    private suspend fun handleReadTasks(case: CaseInfo, audioFile: File) {
        // No need to upload audio for READ intent
        audioFile.delete()

        try {
            val tasks = apiClient.fetchOpenTasks(case.id)
            if (tasks.isEmpty()) {
                playback.speak("Keine offenen Aufgaben für ${case.name}.")
            } else {
                val intro = "${tasks.size} offene Aufgabe${if (tasks.size > 1) "n" else ""} für ${case.name}:"
                val items = tasks.mapIndexed { i, t -> "${i + 1}. ${t.title}" }
                playback.speak(intro)
                playback.speakSequence(items)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to fetch tasks", e)
            playback.speak("Fehler beim Abrufen der Aufgaben für ${case.name}.")
        }
    }

    // ── Case resolution ─────────────────────────────────────────────

    private suspend fun resolveCase(spokenName: String?): CaseInfo? {
        // Refresh cases if stale
        caseRepo.refreshIfNeeded()

        // Explicit case name provided
        if (spokenName != null) {
            return when (val result = caseRepo.matchCase(spokenName)) {
                is CaseMatchResult.Exact -> result.case
                is CaseMatchResult.Fuzzy -> result.case
                is CaseMatchResult.Ambiguous -> {
                    // Ask disambiguation question
                    val names = result.candidates.joinToString(" oder ") { it.name }
                    playback.speak("Welchen Fall meinst du? $names")
                    // For MVP: use the first candidate
                    result.candidates.firstOrNull()
                }
                is CaseMatchResult.NoMatch -> null
            }
        }

        // No explicit name → check last active case (4 min window)
        val recent = settings.getRecentCase()
        if (recent != null) {
            Log.i(TAG, "Using last-active case: ${recent.second}")
            return CaseInfo(id = recent.first, name = recent.second)
        }

        // Check default case
        val defaultId = settings.defaultCaseId
        val defaultName = settings.defaultCaseName
        if (defaultId != null && defaultName != null) {
            return CaseInfo(id = defaultId, name = defaultName)
        }

        return null
    }

    // ── Command SpeechRecognizer (parallel to AudioRecorder) ────────

    private fun startCommandRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return

        commandRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onPartialResults(partialResults: Bundle?) {
                    val texts = partialResults
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!texts.isNullOrEmpty()) {
                        commandTranscript = texts[0]
                    }
                }

                override fun onResults(results: Bundle?) {
                    val texts = results
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!texts.isNullOrEmpty()) {
                        commandTranscript = texts[0]
                    }
                }

                override fun onError(error: Int) {
                    Log.w(TAG, "Command recognizer error: $error")
                }

                override fun onReadyForSpeech(p: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onEndOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })

            val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "de-DE")
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            }
            startListening(intent)
        }
    }

    private fun stopCommandRecognizer() {
        try {
            commandRecognizer?.stopListening()
            commandRecognizer?.destroy()
        } catch (_: Exception) {}
        commandRecognizer = null
    }

    // ── Wakeword management ─────────────────────────────────────────

    private fun startWakewordListening() {
        wakewordEngine.stop()
        wakewordEngine.start(this)
    }

    // ── Notification helpers ────────────────────────────────────────

    private fun buildNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, VoxDocsApp.CHANNEL_LISTENER)
            .setContentTitle("VoxDocs Voice Agent")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_mic)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(android.app.NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID, buildNotification(text))
    }

    // ── Headset detection ───────────────────────────────────────────

    private fun isHeadsetConnected(): Boolean {
        val am = getSystemService(AudioManager::class.java)
        val devices = am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        return devices.any {
            it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
            it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
            it.type == android.media.AudioDeviceInfo.TYPE_WIRED_HEADSET ||
            it.type == android.media.AudioDeviceInfo.TYPE_WIRED_HEADPHONES ||
            it.type == android.media.AudioDeviceInfo.TYPE_BLE_HEADSET
        }
    }

    companion object {
        private const val TAG = "VoiceService"
        private const val NOTIFICATION_ID = 1001
    }
}
