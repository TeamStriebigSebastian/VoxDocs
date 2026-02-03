import { useState, useRef } from 'react'

interface CameraCaptureProps {
  onPhotoCapture: (photoBlob: Blob) => void
}

export default function CameraCapture({ onPhotoCapture }: CameraCaptureProps) {
  const [isCameraActive, setIsCameraActive] = useState(false)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Prefer back camera on mobile
        audio: false,
      })

      setStream(mediaStream)
      setIsCameraActive(true)

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch (error) {
      console.error('Error accessing camera:', error)
      alert('Fehler beim Zugriff auf die Kamera. Bitte Berechtigungen prüfen.')
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setIsCameraActive(false)
  }

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw video frame to canvas
    const context = canvas.getContext('2d')
    if (!context) return

    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Convert canvas to blob
    canvas.toBlob((blob) => {
      if (blob) {
        onPhotoCapture(blob)
        stopCamera()
      }
    }, 'image/jpeg', 0.95)
  }

  return (
    <div className="space-y-4">
      {!isCameraActive ? (
        <button
          onClick={startCamera}
          className="btn btn-primary w-full flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>Kamera öffnen</span>
        </button>
      ) : (
        <div className="space-y-3">
          <div className="relative bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="w-full"
            />
          </div>

          <canvas ref={canvasRef} className="hidden" />

          <div className="flex space-x-3">
            <button
              onClick={stopCamera}
              className="btn flex-1 bg-slate-200 hover:bg-slate-300 text-slate-800"
            >
              Abbrechen
            </button>
            <button
              onClick={capturePhoto}
              className="btn btn-primary flex-1"
            >
              Foto aufnehmen
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
