import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWebSocketNotifications } from '../hooks/useWebSocketNotifications'

interface Notification {
  appointment_uuid: string
  message: string
  timestamp: string
}

export default function TranscriptionNotification() {
  const navigate = useNavigate()
  const [notification, setNotification] = useState<Notification | null>(null)
  const [isVisible, setIsVisible] = useState(false)

  useWebSocketNotifications((data) => {
    // Show notification when transcription is ready
    setNotification({
      appointment_uuid: data.appointment_uuid,
      message: data.message,
      timestamp: data.timestamp,
    })
    setIsVisible(true)

    // Show browser notification if permitted
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('VoxDocs Pflegedienst', {
        body: data.message,
        icon: '/icon-192x192.png',
        badge: '/icon-192x192.png',
        tag: `transcription-${data.appointment_uuid}`,
        requireInteraction: true,
      })
    }

    // Play notification sound (optional)
    try {
      const audio = new Audio('/notification.mp3')
      audio.volume = 0.5
      audio.play().catch(() => {
        // Ignore if audio playback fails (e.g., no user interaction yet)
      })
    } catch (err) {
      console.error('Error playing notification sound:', err)
    }
  })

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  const handleCheck = () => {
    if (notification) {
      navigate(`/appointment/${notification.appointment_uuid}/review`)
      setIsVisible(false)
      setNotification(null)
    }
  }

  const handleDismiss = () => {
    setIsVisible(false)
    setTimeout(() => setNotification(null), 300) // Wait for animation
  }

  if (!isVisible || !notification) {
    return null
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={handleDismiss}
      />

      {/* Notification Popup */}
      <div className="fixed inset-x-4 top-20 z-50 max-w-md mx-auto animate-slide-down">
        <div className="bg-white rounded-lg shadow-2xl border-2 border-primary-500 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-4">
            <div className="flex items-center space-x-3">
              <div className="bg-white rounded-full p-2">
                <svg className="w-6 h-6 text-primary-600 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-white font-bold text-lg">Transkription fertig!</h3>
                <p className="text-primary-100 text-sm">
                  {new Date(notification.timestamp).toLocaleTimeString('de-DE')}
                </p>
              </div>
              <button
                onClick={handleDismiss}
                className="text-white hover:bg-primary-700 rounded-full p-1 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            <div className="flex items-start space-x-3 mb-6">
              <div className="bg-primary-50 rounded-lg p-2">
                <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p className="text-slate-700 font-medium mb-1">
                  {notification.message}
                </p>
                <p className="text-sm text-slate-500">
                  Die Pflegedokumentation wurde erfolgreich verarbeitet und kann jetzt geprüft werden.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex space-x-3">
              <button
                onClick={handleDismiss}
                className="flex-1 btn bg-slate-100 hover:bg-slate-200 text-slate-700 py-3"
              >
                Später
              </button>
              <button
                onClick={handleCheck}
                className="flex-2 btn btn-primary py-3 flex items-center justify-center space-x-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span>Prüfen</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Add animation styles */}
      <style>{`
        @keyframes slide-down {
          from {
            opacity: 0;
            transform: translateY(-2rem);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-slide-down {
          animation: slide-down 0.3s ease-out;
        }
      `}</style>
    </>
  )
}
