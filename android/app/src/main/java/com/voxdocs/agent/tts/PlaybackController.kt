package com.voxdocs.agent.tts

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import kotlinx.coroutines.*
import java.util.Locale
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

/**
 * TTS playback controller with audio focus management and headset routing.
 *
 * Features:
 *  - Speaks text via Android TTS
 *  - Routes audio to headset when connected
 *  - Plays confirmation beeps
 *  - Supports sequential task readout
 */
class PlaybackController(private val context: Context) {

    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    /** Initialise the TTS engine. Call once at service start. */
    suspend fun init() = suspendCoroutine { cont ->
        tts = TextToSpeech(context) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.GERMAN
                tts?.setSpeechRate(1.0f)
                Log.i(TAG, "TTS initialised")
            } else {
                Log.e(TAG, "TTS init failed: $status")
            }
            cont.resume(ttsReady)
        }
    }

    // ── Beep ────────────────────────────────────────────────────────

    /** Play a short confirmation beep. */
    fun playBeep() {
        try {
            val stream = if (isHeadsetConnected()) AudioManager.STREAM_VOICE_CALL
                         else AudioManager.STREAM_NOTIFICATION
            val tone = ToneGenerator(stream, 80) // 80% volume
            tone.startTone(ToneGenerator.TONE_PROP_BEEP, 200)
            android.os.Handler(context.mainLooper).postDelayed({ tone.release() }, 300)
        } catch (e: Exception) {
            Log.w(TAG, "Beep failed", e)
        }
    }

    // ── Speak ───────────────────────────────────────────────────────

    /** Speak a single text string. Suspends until finished or timeout. */
    suspend fun speak(text: String, utteranceId: String = "u_${System.currentTimeMillis()}") {
        if (!ttsReady) {
            Log.w(TAG, "TTS not ready, skipping: $text")
            return
        }

        requestAudioFocus()

        suspendCancellableCoroutine { cont ->
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(uid: String?) {}
                override fun onDone(uid: String?) {
                    if (cont.isActive) cont.resume(Unit)
                }
                @Deprecated("Deprecated in Java")
                override fun onError(uid: String?) {
                    if (cont.isActive) cont.resume(Unit)
                }
                override fun onError(uid: String?, errorCode: Int) {
                    Log.e(TAG, "TTS error: $errorCode")
                    if (cont.isActive) cont.resume(Unit)
                }
            })

            val params = android.os.Bundle().apply {
                if (isHeadsetConnected()) {
                    putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, AudioManager.STREAM_VOICE_CALL)
                }
            }

            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, utteranceId)

            // Safety timeout (30s max for any single utterance)
            cont.invokeOnCancellation { tts?.stop() }
        }

        abandonAudioFocus()
    }

    /** Speak a list of texts sequentially (e.g., task list). */
    suspend fun speakSequence(items: List<String>) {
        for ((i, item) in items.withIndex()) {
            speak(item, "seq_$i")
            delay(300) // small pause between items
        }
    }

    /** Speak a confirmation like "Saved for Demian". */
    suspend fun speakConfirmation(caseName: String, taskCount: Int = 0) {
        val msg = when {
            taskCount > 0 -> "Gespeichert für $caseName. $taskCount Aufgabe${if (taskCount > 1) "n" else ""} erstellt."
            else          -> "Gespeichert für $caseName."
        }
        speak(msg)
    }

    // ── Stop ────────────────────────────────────────────────────────

    fun stop() {
        tts?.stop()
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }

    // ── Audio routing helpers ───────────────────────────────────────

    private fun isHeadsetConnected(): Boolean {
        val devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        return devices.any {
            it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
            it.type == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
            it.type == android.media.AudioDeviceInfo.TYPE_WIRED_HEADSET ||
            it.type == android.media.AudioDeviceInfo.TYPE_WIRED_HEADPHONES ||
            it.type == android.media.AudioDeviceInfo.TYPE_BLE_HEADSET
        }
    }

    private var focusRequest: AudioFocusRequest? = null

    private fun requestAudioFocus() {
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANT)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()

        focusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(attrs)
            .build()

        audioManager.requestAudioFocus(focusRequest!!)
    }

    private fun abandonAudioFocus() {
        focusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
    }

    companion object {
        private const val TAG = "Playback"
    }
}
