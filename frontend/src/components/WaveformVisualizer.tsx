import { useEffect, useRef, useState } from 'react'

interface WaveformVisualizerProps {
  isRecording: boolean
  audioStream?: MediaStream | null
}

export default function WaveformVisualizer({ isRecording, audioStream }: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const analyzerRef = useRef<AnalyserNode>()
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null)

  useEffect(() => {
    if (!isRecording || !audioStream) {
      // Clear canvas when not recording
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d')
        if (ctx) {
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
        }
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      return
    }

    // Initialize audio context and analyzer
    const ctx = new AudioContext()

    // Resume AudioContext if suspended (Chrome requires user gesture)
    if (ctx.state === 'suspended') {
      ctx.resume()
    }

    setAudioContext(ctx)

    const analyzer = ctx.createAnalyser()
    analyzer.fftSize = 256
    analyzerRef.current = analyzer

    const source = ctx.createMediaStreamSource(audioStream)
    source.connect(analyzer)

    // Start visualization
    const bufferLength = analyzer.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    const draw = () => {
      if (!canvasRef.current || !isRecording) return

      const canvas = canvasRef.current
      const canvasCtx = canvas.getContext('2d')
      if (!canvasCtx) return

      animationRef.current = requestAnimationFrame(draw)

      analyzer.getByteFrequencyData(dataArray)

      // Clear canvas
      canvasCtx.fillStyle = '#f8fafc'
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height)

      // Draw bars
      const barWidth = (canvas.width / bufferLength) * 2.5
      let x = 0

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height * 0.8

        // Gradient from dental blue to lighter blue
        const gradient = canvasCtx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height)
        gradient.addColorStop(0, '#0ea5e9')
        gradient.addColorStop(1, '#0284c7')
        canvasCtx.fillStyle = gradient

        // Center the bars vertically
        const y = (canvas.height - barHeight) / 2
        canvasCtx.fillRect(x, y, barWidth - 1, barHeight)

        x += barWidth + 1
      }
    }

    draw()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      if (audioContext) {
        audioContext.close()
      }
    }
  }, [isRecording, audioStream])

  return (
    <div className="w-full h-24 bg-slate-100 rounded-lg overflow-hidden">
      <canvas
        ref={canvasRef}
        width={400}
        height={96}
        className="w-full h-full"
      />
      {!isRecording && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex gap-1">
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-slate-300 rounded-full"
                style={{ height: `${Math.random() * 40 + 10}px` }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
