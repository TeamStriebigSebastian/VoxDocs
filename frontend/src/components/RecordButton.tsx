import { useCallback, useRef } from 'react'

interface RecordButtonProps {
  isRecording: boolean
  isPaused?: boolean
  onStart: () => void
  onStop: () => void
  onPause?: () => void
  onResume?: () => void
  disabled?: boolean
  pushToTalk?: boolean  // PTT mode: hold to record
}

export default function RecordButton({
  isRecording,
  onStart,
  onStop,
  disabled = false,
  pushToTalk = false,
}: RecordButtonProps) {
  const isHolding = useRef(false)

  // Toggle mode: click to start/stop
  const handleClick = useCallback(() => {
    if (disabled || pushToTalk) return
    if (isRecording) {
      onStop()
    } else {
      onStart()
    }
  }, [disabled, pushToTalk, isRecording, onStart, onStop])

  // PTT mode: press to start
  const handlePressStart = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (disabled || !pushToTalk) return
    e.preventDefault()  // Prevent context menu on long press
    if (!isRecording && !isHolding.current) {
      isHolding.current = true
      onStart()
    }
  }, [disabled, pushToTalk, isRecording, onStart])

  // PTT mode: release to stop
  const handlePressEnd = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (disabled || !pushToTalk) return
    e.preventDefault()
    if (isRecording && isHolding.current) {
      isHolding.current = false
      onStop()
    }
  }, [disabled, pushToTalk, isRecording, onStop])

  // Prevent context menu on long press (mobile)
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    if (pushToTalk) {
      e.preventDefault()
    }
  }, [pushToTalk])

  return (
    <div className="flex flex-col items-center space-y-3">
      <button
        onClick={handleClick}
        onMouseDown={handlePressStart}
        onMouseUp={handlePressEnd}
        onMouseLeave={handlePressEnd}
        onTouchStart={handlePressStart}
        onTouchEnd={handlePressEnd}
        onTouchCancel={handlePressEnd}
        onContextMenu={handleContextMenu}
        disabled={disabled}
        className={`
          relative w-32 h-32 rounded-full transition-all duration-300
          focus:outline-none focus:ring-4 focus:ring-offset-2
          select-none touch-none
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${isRecording
            ? 'bg-red-500 hover:bg-red-600 focus:ring-red-300 recording-pulse'
            : 'bg-dental-600 hover:bg-dental-700 focus:ring-dental-300'
          }
        `}
        aria-label={isRecording ? 'Aufnahme stoppen' : 'Aufnahme starten'}
      >
        {/* Inner circle/square indicator */}
        <div className="absolute inset-0 flex items-center justify-center">
          {isRecording ? (
            // Stop icon (square)
            <div className="w-10 h-10 bg-white rounded-md" />
          ) : pushToTalk ? (
            // PTT: Hand/finger icon
            <svg
              className="w-16 h-16 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"
              />
            </svg>
          ) : (
            // Normal: Mic icon
            <svg
              className="w-16 h-16 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          )}
        </div>

        {/* Pulse rings when recording */}
        {isRecording && (
          <>
            <span className="absolute inset-0 rounded-full bg-red-400 animate-ping opacity-25" />
            <span className="absolute inset-[-8px] rounded-full border-4 border-red-300 opacity-50" />
          </>
        )}
      </button>

      {/* Mode indicator */}
      <span className="text-xs text-slate-500">
        {pushToTalk ? 'Gedrückt halten zum Aufnehmen' : 'Tippen zum Starten/Stoppen'}
      </span>
    </div>
  )
}
