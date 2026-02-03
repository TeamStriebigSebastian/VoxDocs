import { useState, useRef, useEffect } from 'react'
import { Square, Play, Pause } from 'lucide-react'

interface AudioRecorderProps {
    onRecordingComplete: (file: File) => void
    onCancel: () => void
}

export default function AudioRecorder({ onRecordingComplete, onCancel }: AudioRecorderProps) {
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
    const [isPlaying, setIsPlaying] = useState(false)

    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const chunksRef = useRef<Blob[]>([])
    const timerRef = useRef<number | null>(null)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    useEffect(() => {
        startRecording()
        return () => {
            stopRecordingContext()
        }
    }, [])

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            mediaRecorderRef.current = new MediaRecorder(stream)
            chunksRef.current = []

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data)
                }
            }

            mediaRecorderRef.current.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                setAudioBlob(blob)
                stopRecordingContext()
            }

            mediaRecorderRef.current.start()
            setIsRecording(true)

            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1)
            }, 1000)

        } catch (err) {
            console.error('Error accessing microphone:', err)
            alert('Mikrofonzugriff verweigert oder nicht verfügbar.')
            onCancel()
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            setIsRecording(false)
        }
    }

    const stopRecordingContext = () => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }
        if (mediaRecorderRef.current?.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
        }
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
        const secs = (seconds % 60).toString().padStart(2, '0')
        return `${mins}:${secs}`
    }

    const handleConfirm = () => {
        if (audioBlob) {
            const file = new File([audioBlob], "recording.webm", { type: 'audio/webm' })
            onRecordingComplete(file)
        }
    }

    const togglePreview = () => {
        if (!audioRef.current && audioBlob) {
            const url = URL.createObjectURL(audioBlob)
            audioRef.current = new Audio(url)
            audioRef.current.onended = () => setIsPlaying(false)
        }

        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause()
            } else {
                audioRef.current.play()
            }
            setIsPlaying(!isPlaying)
        }
    }

    if (audioBlob) {
        return (
            <div className="flex items-center space-x-3 bg-slate-100 p-2 rounded-lg border border-slate-200">
                <button
                    type="button"
                    onClick={togglePreview}
                    className="p-2 rounded-full bg-white text-slate-700 hover:text-blue-600 shadow-sm transition-colors"
                >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <div className="text-sm font-medium text-slate-600">
                    Aufnahme fertig ({formatTime(recordingTime)})
                </div>
                <div className="flex items-center ml-auto pl-2 border-l border-slate-300 space-x-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="p-1 px-2 text-xs text-red-500 hover:bg-red-50 rounded"
                    >
                        Löschen
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        className="p-1 px-3 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Verwenden
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="flex items-center space-x-4 bg-red-50 p-3 rounded-lg border border-red-100 animate-pulse">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-ping" />
            <div className="flex-1 font-medium text-red-700">
                Aufnahme läuft... {formatTime(recordingTime)}
            </div>
            <button
                type="button"
                onClick={stopRecording}
                className="p-2 bg-white text-red-600 rounded-full shadow-sm hover:bg-red-100 transition-colors"
            >
                <Square className="w-5 h-5 fill-current" />
            </button>
        </div>
    )
}
