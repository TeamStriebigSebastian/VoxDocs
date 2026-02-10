package com.voxdocs.agent.wakeword

/**
 * Abstraction for wakeword detection engines.
 *
 * Implementations:
 *  - [SpeechRecognizerWakeword] — uses Android SpeechRecognizer (works immediately, needs internet on some devices)
 *  - PorcupineWakewordEngine    — placeholder for Picovoice Porcupine (fully offline, requires API key)
 *
 * To swap engines, just change which implementation is instantiated in [VoiceListenerService].
 */
interface WakewordEngine {

    /** Start listening for the wakeword. Calls [listener] on detection. */
    fun start(listener: WakewordListener)

    /** Stop listening and release resources. */
    fun stop()

    /** Whether the engine is currently listening. */
    val isListening: Boolean

    interface WakewordListener {
        /** Called when the wakeword is detected. */
        fun onWakewordDetected()

        /** Called when the engine encounters a non-fatal error and will retry. */
        fun onError(message: String)
    }
}
