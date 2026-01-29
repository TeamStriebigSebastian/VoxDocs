import { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, Square, Loader2 } from 'lucide-react'

interface SmartVoiceButtonProps {
    onRecordingComplete: (file: File) => void
    isProcessing?: boolean
}

export default function SmartVoiceButton({ onRecordingComplete, isProcessing = false }: SmartVoiceButtonProps) {
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const [mode, setMode] = useState<'idle' | 'hold' | 'toggle'>('idle')

    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const chunksRef = useRef<Blob[]>([])
    const timerRef = useRef<number | null>(null)
    const holdStartRef = useRef<number>(0)

    // Lock to prevent race conditions during rapid clicks
    const isInitializingRef = useRef(false)
    const isRecordingRef = useRef(false) // Sync ref for async handlers

    // Minimum duration to consider it a "Hold" (Push-to-Talk)
    const HOLD_THRESHOLD_MS = 300

    useEffect(() => {
        return () => stopRecordingContext()
    }, [])

    // Keep ref in sync with state
    useEffect(() => {
        isRecordingRef.current = isRecording
    }, [isRecording])

    const stopRecordingContext = useCallback(() => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }
        if (mediaRecorderRef.current?.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
        }
        mediaRecorderRef.current = null
        isInitializingRef.current = false
    }, [])

    const startRecording = useCallback(async (): Promise<boolean> => {
        // Prevent double-activation
        if (isInitializingRef.current || isRecordingRef.current) {
            console.log('[SmartVoiceButton] Already recording or initializing, ignoring.')
            return false
        }

        isInitializingRef.current = true

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

            // Double-check we weren't cancelled during await
            if (!isInitializingRef.current) {
                stream.getTracks().forEach(track => track.stop())
                return false
            }

            const mediaRecorder = new MediaRecorder(stream)
            mediaRecorderRef.current = mediaRecorder
            chunksRef.current = []

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data)
            }

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                const file = new File([blob], "recording.webm", { type: 'audio/webm' })

                // Safe callback with error boundary
                try {
                    onRecordingComplete(file)
                } catch (err) {
                    console.error('[SmartVoiceButton] Error in onRecordingComplete:', err)
                }

                stopRecordingContext()
            }

            mediaRecorder.start()
            setIsRecording(true)
            isInitializingRef.current = false

            // UI Timer
            setRecordingTime(0)
            timerRef.current = window.setInterval(() => {
                setRecordingTime(prev => prev + 1)
            }, 1000)

            return true
        } catch (err) {
            console.error('[SmartVoiceButton] Mic Access Error:', err)
            isInitializingRef.current = false
            return false
        }
    }, [onRecordingComplete, stopRecordingContext])

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try {
                mediaRecorderRef.current.stop()
            } catch (err) {
                console.error('[SmartVoiceButton] Error stopping recorder:', err)
            }
        }
        setIsRecording(false)
        setMode('idle')
    }, [])

    // --- Interaction Handlers ---

    const handlePointerDown = useCallback(async (e: React.PointerEvent) => {
        if (isProcessing || isInitializingRef.current) return

        e.preventDefault()
        holdStartRef.current = Date.now()

        // If already recording (toggle mode), this down event will be handled in up
        if (!isRecordingRef.current) {
            const started = await startRecording()
            if (started) {
                setMode('hold') // Assume hold initially
            }
        }
    }, [isProcessing, startRecording])

    const handlePointerUp = useCallback((e: React.PointerEvent) => {
        if (isProcessing) return
        e.preventDefault()

        const duration = Date.now() - holdStartRef.current

        if (isRecordingRef.current) {
            if (mode === 'toggle') {
                // We were in toggle mode, clicking again stops it
                stopRecording()
            } else {
                // We were in 'hold' mode (initial press)
                if (duration < HOLD_THRESHOLD_MS) {
                    // Short tap -> Switch to Toggle Mode (keep recording)
                    setMode('toggle')
                } else {
                    // Long press -> Stop recording (Push-to-Talk)
                    stopRecording()
                }
            }
        }
    }, [isProcessing, mode, stopRecording])

    // Special handler for the 'toggle' mode stop
    // If we are in toggle mode, the user expects to click to stop.
    // However, the pointerDown usually starts stuff. 
    // We handle the "Stop" logic in PointerUp usually, but if we are already recording in Toggle mode,
    // the next Down/Up cycle should stop it.

    // Actually, simpler logic:
    // If NOT recording: Down -> Start, Assume Hold.
    // If Recording AND Mode is Hold: Up -> Check Duration. Short? Switch to Toggle. Long? Stop.
    // If Recording AND Mode is Toggle: Up -> Stop.


    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
        const secs = (seconds % 60).toString().padStart(2, '0')
        return `${mins}:${secs}`
    }

    return (
        <div className="flex flex-col items-center">
            {/* Timer Overlay (Floating above or below) */}
            {isRecording && (
                <div className="absolute -top-10 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded-full animate-pulse">
                    {formatTime(recordingTime)}
                </div>
            )}

            <button
                onPointerDown={handlePointerDown}
                onPointerUp={handlePointerUp}
                onPointerLeave={() => {
                    // If dragging finger off while holding, usually means cancel or stop. 
                    // For safety in medical context, let's treat it as "Send" (Stop) if holding.
                    if (isRecording && mode === 'hold') stopRecording()
                }}
                className={`
                    flex items-center justify-center rounded-full shadow-xl transition-all duration-200 border-4 
                    ${isRecording
                        ? 'w-24 h-24 bg-white border-red-500 scale-110'
                        : 'w-20 h-20 bg-red-500 hover:bg-red-600 border-slate-50 hover:scale-105 active:scale-95'
                    }
                    ${isProcessing ? 'opacity-70 cursor-wait' : ''}
                `}
                title={isRecording ? "Loslassen zum Senden" : "Gedrückt halten oder Antippen"}
            >
                {isProcessing ? (
                    <Loader2 className="w-8 h-8 text-white animate-spin" />
                ) : isRecording ? (
                    <Square className="w-8 h-8 text-red-500 fill-current" />
                ) : (
                    <Mic className="w-9 h-9 text-white" />
                )}
            </button>
            <p className="mt-2 text-[10px] font-medium text-slate-400 uppercase tracking-wide">
                {isRecording ? (mode === 'toggle' ? "Antippen zum Senden" : "Sprechen...") : "Aufnahme"}
            </p>
        </div>
    )
}
