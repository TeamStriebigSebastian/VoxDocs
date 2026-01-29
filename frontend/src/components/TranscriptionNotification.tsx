import { useState } from 'react'
import { useWebSocketNotifications } from '../hooks/useWebSocketNotifications'
import { CheckCircle2, X } from 'lucide-react'

interface Notification {
  appointment_uuid: string
  message: string
  timestamp: string
}

export default function TranscriptionNotification() {
  const [notification, setNotification] = useState<Notification | null>(null)
  const [isVisible, setIsVisible] = useState(false)

  useWebSocketNotifications((data) => {
    // Show notification when transcription is ready
    setNotification({
      appointment_uuid: data.appointment_uuid,
      message: "Transkription und Aufgaben verarbeitet", // Generic Platform Message
      timestamp: data.timestamp,
    })
    setIsVisible(true)

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      setIsVisible(false)
      setTimeout(() => setNotification(null), 300)
    }, 4000)

    // Play notification sound (subtle)
    try {
      const audio = new Audio('/notification.mp3')
      audio.volume = 0.2
      audio.play().catch(() => { })
    } catch (err) {
      console.error('Error playing notification sound:', err)
    }
  })

  if (!isVisible || !notification) {
    return null
  }

  return (
    <div className="fixed top-20 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
      <div className="bg-white rounded-lg shadow-lg border-l-4 border-green-500 p-4 max-w-sm flex items-start space-x-3">
        <div className="flex-shrink-0">
          <CheckCircle2 className="w-5 h-5 text-green-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            Fertig!
          </p>
          <p className="text-sm text-gray-500 truncate">
            {notification.message}
          </p>
        </div>
        <div className="flex-shrink-0 flex">
          <button
            onClick={() => setIsVisible(false)}
            className="rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
          >
            <span className="sr-only">Close</span>
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
