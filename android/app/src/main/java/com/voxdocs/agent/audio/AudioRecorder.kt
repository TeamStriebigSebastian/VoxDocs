package com.voxdocs.agent.audio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile

/**
 * Records audio from the microphone to a WAV file (PCM 16-bit, 16 kHz, mono).
 *
 * Features:
 *  - Configurable max duration
 *  - Simple amplitude-based VAD (voice-activity detection) to auto-stop on silence
 *  - Writes proper WAV headers so Whisper can process the file directly
 */
class AudioRecorder {

    private var audioRecord: AudioRecord? = null
    private var recordingJob: Job? = null
    @Volatile private var _isRecording = false

    val isRecording: Boolean get() = _isRecording

    /**
     * Start recording. Returns the output WAV [File] once recording finishes.
     *
     * @param outputFile   Where to write the WAV
     * @param maxDurationMs  Hard stop after this many milliseconds (default 45 s)
     * @param silenceTimeoutMs  Stop after this many ms of silence (default 2 s)
     * @param silenceThreshold  RMS amplitude below which audio is considered silent
     */
    suspend fun record(
        outputFile: File,
        maxDurationMs: Long = 45_000,
        silenceTimeoutMs: Long = 2_000,
        silenceThreshold: Short = 500,
    ): File = withContext(Dispatchers.IO) {

        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT
        ).coerceAtLeast(BUFFER_SIZE)

        val recorder = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT,
            bufferSize
        )

        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            throw IllegalStateException("AudioRecord failed to initialize")
        }

        audioRecord = recorder
        _isRecording = true

        val fos = FileOutputStream(outputFile)
        // Write placeholder WAV header (44 bytes); we patch it at the end.
        val header = ByteArray(44)
        fos.write(header)

        var totalBytes = 0L
        var silentMs = 0L
        val startTime = System.currentTimeMillis()
        val buffer = ShortArray(bufferSize / 2)

        try {
            recorder.startRecording()
            Log.i(TAG, "Recording started → ${outputFile.name}")

            while (_isRecording) {
                val elapsed = System.currentTimeMillis() - startTime
                if (elapsed >= maxDurationMs) {
                    Log.i(TAG, "Max duration reached (${maxDurationMs}ms)")
                    break
                }

                val read = recorder.read(buffer, 0, buffer.size)
                if (read <= 0) continue

                // Write PCM data
                val byteBuffer = ByteArray(read * 2)
                for (i in 0 until read) {
                    byteBuffer[i * 2]     = (buffer[i].toInt() and 0xFF).toByte()
                    byteBuffer[i * 2 + 1] = (buffer[i].toInt() shr 8 and 0xFF).toByte()
                }
                fos.write(byteBuffer, 0, read * 2)
                totalBytes += read * 2

                // VAD: compute RMS amplitude
                val rms = computeRms(buffer, read)
                val chunkMs = (read * 1000L) / SAMPLE_RATE
                if (rms < silenceThreshold) {
                    silentMs += chunkMs
                    if (silentMs >= silenceTimeoutMs && totalBytes > SAMPLE_RATE * 2) {
                        // Only stop on silence if we've recorded at least 1 second
                        Log.i(TAG, "Silence detected (${silentMs}ms)")
                        break
                    }
                } else {
                    silentMs = 0
                }
            }
        } finally {
            recorder.stop()
            recorder.release()
            audioRecord = null
            _isRecording = false
            fos.close()
        }

        // Patch WAV header with actual sizes
        patchWavHeader(outputFile, totalBytes)
        Log.i(TAG, "Recording saved: ${outputFile.length()} bytes")

        outputFile
    }

    /** Stop the current recording. */
    fun stop() {
        _isRecording = false
    }

    // ── WAV header helpers ──────────────────────────────────────────

    private fun patchWavHeader(file: File, dataSize: Long) {
        RandomAccessFile(file, "rw").use { raf ->
            val totalSize = dataSize + 36
            raf.seek(0)
            raf.write("RIFF".toByteArray())
            raf.write(intToLittleEndian(totalSize.toInt()))
            raf.write("WAVE".toByteArray())
            raf.write("fmt ".toByteArray())
            raf.write(intToLittleEndian(16))          // Subchunk1Size (PCM)
            raf.write(shortToLittleEndian(1))          // AudioFormat (PCM=1)
            raf.write(shortToLittleEndian(1))          // NumChannels (mono)
            raf.write(intToLittleEndian(SAMPLE_RATE))  // SampleRate
            raf.write(intToLittleEndian(SAMPLE_RATE * 2)) // ByteRate
            raf.write(shortToLittleEndian(2))          // BlockAlign
            raf.write(shortToLittleEndian(16))         // BitsPerSample
            raf.write("data".toByteArray())
            raf.write(intToLittleEndian(dataSize.toInt()))
        }
    }

    private fun computeRms(buffer: ShortArray, count: Int): Short {
        var sum = 0L
        for (i in 0 until count) {
            sum += buffer[i].toLong() * buffer[i].toLong()
        }
        return Math.sqrt((sum.toDouble() / count)).toInt().toShort()
    }

    private fun intToLittleEndian(value: Int) = byteArrayOf(
        (value and 0xFF).toByte(),
        (value shr 8 and 0xFF).toByte(),
        (value shr 16 and 0xFF).toByte(),
        (value shr 24 and 0xFF).toByte()
    )

    private fun shortToLittleEndian(value: Int) = byteArrayOf(
        (value and 0xFF).toByte(),
        (value shr 8 and 0xFF).toByte()
    )

    companion object {
        private const val TAG = "AudioRecorder"
        const val SAMPLE_RATE = 16_000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BUFFER_SIZE = 4096
    }
}
