package com.voxdocs.agent.wakeword

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

/**
 * Wakeword detection using Android's built-in [SpeechRecognizer].
 *
 * Runs continuous recognition and scans each partial/final result for the
 * trigger phrase "voxdocs". On detection it fires [WakewordEngine.WakewordListener.onWakewordDetected]
 * and pauses until [start] is called again (the caller records a command, then restarts).
 *
 * Notes:
 *  - On most Android 13+ devices with downloaded offline language packs this works offline.
 *  - On older devices or without language packs, results are streamed via Google servers.
 *  - This is the MVP fallback; swap with PorcupineWakewordEngine for guaranteed offline.
 */
class SpeechRecognizerWakeword(
    private val context: Context,
) : WakewordEngine {

    private var recognizer: SpeechRecognizer? = null
    private var listener: WakewordEngine.WakewordListener? = null
    private var _isListening = false
    private var detected = false

    override val isListening: Boolean get() = _isListening

    override fun start(listener: WakewordEngine.WakewordListener) {
        this.listener = listener
        detected = false
        startRecognizer()
    }

    override fun stop() {
        _isListening = false
        try {
            recognizer?.cancel()
            recognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping recognizer", e)
        }
        recognizer = null
    }

    // ── internal ────────────────────────────────────────────────────

    private fun startRecognizer() {
        if (detected) return
        stop() // clean up any existing instance

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            listener?.onError("Speech recognition not available on this device")
            return
        }

        recognizer = SpeechRecognizer.createSpeechRecognizer(context).also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {

                override fun onReadyForSpeech(params: Bundle?) {
                    _isListening = true
                    Log.d(TAG, "Listening for wakeword…")
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    val texts = partialResults
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    texts?.forEach { checkForTrigger(it) }
                }

                override fun onResults(results: Bundle?) {
                    val texts = results
                        ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    texts?.forEach { checkForTrigger(it) }
                    // Restart for continuous listening (unless wakeword was found)
                    if (!detected) restartAfterDelay()
                }

                override fun onError(error: Int) {
                    _isListening = false
                    val msg = errorCodeToString(error)
                    Log.w(TAG, "Recognition error: $msg ($error)")

                    // Errors 7 (NO_MATCH) and 6 (SPEECH_TIMEOUT) are normal;
                    // just restart. Others worth logging.
                    if (error != SpeechRecognizer.ERROR_NO_MATCH
                        && error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                        listener?.onError(msg)
                    }
                    if (!detected) restartAfterDelay()
                }

                override fun onBeginningOfSpeech() {}
                override fun onEndOfSpeech() { _isListening = false }
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })

            sr.startListening(createIntent())
        }
    }

    private fun createIntent() = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        // Accept both German and English
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "de-DE")
    }

    private fun checkForTrigger(text: String) {
        val lower = text.lowercase()
        if (TRIGGER_PHRASES.any { it in lower }) {
            Log.i(TAG, "Wakeword detected in: \"$text\"")
            detected = true
            _isListening = false
            recognizer?.cancel()
            listener?.onWakewordDetected()
        }
    }

    private fun restartAfterDelay() {
        // Small delay to avoid tight loop on repeated errors
        android.os.Handler(context.mainLooper).postDelayed({
            if (!detected) startRecognizer()
        }, 500)
    }

    private fun errorCodeToString(code: Int): String = when (code) {
        SpeechRecognizer.ERROR_AUDIO              -> "AUDIO"
        SpeechRecognizer.ERROR_CLIENT              -> "CLIENT"
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "PERMISSIONS"
        SpeechRecognizer.ERROR_NETWORK             -> "NETWORK"
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT     -> "NETWORK_TIMEOUT"
        SpeechRecognizer.ERROR_NO_MATCH            -> "NO_MATCH"
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY     -> "BUSY"
        SpeechRecognizer.ERROR_SERVER              -> "SERVER"
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT      -> "SPEECH_TIMEOUT"
        else -> "UNKNOWN($code)"
    }

    companion object {
        private const val TAG = "WakewordSR"
        /** Phrases to detect in the transcript. */
        private val TRIGGER_PHRASES = listOf("voxdocs", "vox docs", "foxdocs", "box docs")
    }
}
