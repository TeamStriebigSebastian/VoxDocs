interface RecordButtonProps {
  isRecording: boolean
  isPaused?: boolean
  onStart: () => void
  onStop: () => void
  onPause?: () => void
  onResume?: () => void
  disabled?: boolean
}

export default function RecordButton({
  isRecording,
  onStart,
  onStop,
  disabled = false,
}: RecordButtonProps) {
  const handleClick = () => {
    if (disabled) return
    if (isRecording) {
      onStop()
    } else {
      onStart()
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={`
        relative w-32 h-32 rounded-full transition-all duration-300
        focus:outline-none focus:ring-4 focus:ring-offset-2
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
        ) : (
          // Mic icon
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
  )
}
