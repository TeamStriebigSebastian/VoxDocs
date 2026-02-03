import { useEffect, useRef, useState } from 'react'

interface TranscriptionReadyNotification {
  type: 'transcription_ready'
  appointment_uuid: string
  timestamp: string
  message: string
}

type NotificationCallback = (notification: TranscriptionReadyNotification) => void

export function useWebSocketNotifications(onNotification?: NotificationCallback) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const onNotificationRef = useRef(onNotification)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    onNotificationRef.current = onNotification
  }, [onNotification])

  useEffect(() => {
    connectWebSocket()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      // Determine WebSocket URL based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/api/webhooks/ws`

      console.log('Connecting to WebSocket:', wsUrl)

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setError(null)

        // Send heartbeat every 30 seconds
        const heartbeat = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)

        ws.addEventListener('close', () => {
          clearInterval(heartbeat)
        })
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'transcription_ready') {
            console.log('Transcription ready notification received:', data)
            onNotificationRef.current?.(data)
          } else if (data.type === 'pong') {
            // Heartbeat response
            console.log('Heartbeat pong received')
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setIsConnected(false)

        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connectWebSocket()
        }, 5000)
      }
    } catch (err) {
      console.error('Error creating WebSocket:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return {
    isConnected,
    error,
  }
}
