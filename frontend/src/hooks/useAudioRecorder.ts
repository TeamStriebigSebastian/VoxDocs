import { useState, useRef, useCallback } from 'react'

interface UseAudioRecorderOptions {
  onRecordingComplete?: (blob: Blob, duration: number) => void
  onError?: (error: Error) => void
}

interface UseAudioRecorderReturn {
  isRecording: boolean
  isPaused: boolean
  duration: number
  audioStream: MediaStream | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  pauseRecording: () => void
  resumeRecording: () => void
  error: Error | null
}

export function useAudioRecorder(options: UseAudioRecorderOptions = {}): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [duration, setDuration] = useState(0)
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      chunksRef.current = []

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000, // Optimal for Whisper
        }
      })

      setAudioStream(stream)

      // Create MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      })

      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        const finalDuration = (Date.now() - startTimeRef.current) / 1000

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
        setAudioStream(null)
        setDuration(0) // Reset duration for next recording

        // Only call callback if we have actual data
        if (options.onRecordingComplete && blob.size > 0 && finalDuration >= 0.5) {
          options.onRecordingComplete(blob, finalDuration)
        } else if (blob.size === 0) {
          console.warn('Recording produced empty blob, discarding')
        } else if (finalDuration < 0.5) {
          console.warn('Recording too short (<0.5s), discarding')
        }
      }

      mediaRecorder.onerror = () => {
        const err = new Error('Recording error occurred')
        setError(err)
        if (options.onError) {
          options.onError(err)
        }
      }

      // Start recording
      mediaRecorder.start(1000) // Collect data every second
      startTimeRef.current = Date.now()
      setIsRecording(true)
      setIsPaused(false)

      // Start duration timer
      timerRef.current = window.setInterval(() => {
        setDuration((Date.now() - startTimeRef.current) / 1000)
      }, 100)

    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to start recording')
      setError(error)
      if (options.onError) {
        options.onError(error)
      }
    }
  }, [options])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }

    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    setIsRecording(false)
    setIsPaused(false)
  }, [])

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause()
      setIsPaused(true)
    }
  }, [])

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume()
      setIsPaused(false)
    }
  }, [])

  return {
    isRecording,
    isPaused,
    duration,
    audioStream,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    error,
  }
}
