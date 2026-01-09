import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { healthApi } from '../services/api'

export default function SettingsPage() {
  const {
    practiceName,
    rooms,
    selectedRoomId,
    userName,
    processImmediately,
    setSelectedRoom,
    setProcessImmediately,
  } = useAppStore()

  const [serverStatus, setServerStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [queueStats, setQueueStats] = useState<{
    pending: number
    processing: number
    completed: number
  } | null>(null)

  useEffect(() => {
    checkServerStatus()
  }, [])

  const checkServerStatus = async () => {
    setServerStatus('checking')
    try {
      const response = await healthApi.detailed()
      setServerStatus('online')
      if (response.components?.queue?.stats) {
        setQueueStats(response.components.queue.stats)
      }
    } catch {
      setServerStatus('offline')
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-800">Einstellungen</h2>

      {/* Practice info */}
      <div className="card">
        <h3 className="font-medium text-slate-800 mb-4">Praxis</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Name:</span>
            <span className="text-slate-800">{practiceName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Benutzer:</span>
            <span className="text-slate-800">{userName}</span>
          </div>
        </div>
      </div>

      {/* Room selection */}
      <div className="card">
        <h3 className="font-medium text-slate-800 mb-4">Standardraum</h3>
        <select
          value={selectedRoomId || ''}
          onChange={(e) => setSelectedRoom(Number(e.target.value) || null)}
          className="w-full p-3 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-dental-500 focus:border-dental-500"
        >
          <option value="">Kein Standardraum</option>
          {rooms.map((room) => (
            <option key={room.id} value={room.id}>
              {room.name}
            </option>
          ))}
        </select>
      </div>

      {/* Processing settings */}
      <div className="card">
        <h3 className="font-medium text-slate-800 mb-4">Verarbeitung</h3>
        <label className="flex items-center justify-between">
          <div>
            <span className="text-slate-800">Sofortige Verarbeitung</span>
            <p className="text-sm text-slate-500 mt-1">
              Aufnahmen werden sofort transkribiert statt über Nacht
            </p>
          </div>
          <button
            onClick={() => setProcessImmediately(!processImmediately)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              processImmediately ? 'bg-dental-600' : 'bg-slate-300'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                processImmediately ? 'translate-x-7' : 'translate-x-1'
              }`}
            />
          </button>
        </label>
      </div>

      {/* Server status */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-slate-800">Server Status</h3>
          <button
            onClick={checkServerStatus}
            className="text-dental-600 text-sm hover:underline"
          >
            Aktualisieren
          </button>
        </div>

        <div className="flex items-center space-x-2 mb-4">
          <span
            className={`w-3 h-3 rounded-full ${
              serverStatus === 'online'
                ? 'bg-green-500'
                : serverStatus === 'offline'
                ? 'bg-red-500'
                : 'bg-yellow-500 animate-pulse'
            }`}
          />
          <span className="text-sm text-slate-600">
            {serverStatus === 'online'
              ? 'Verbunden'
              : serverStatus === 'offline'
              ? 'Nicht verbunden'
              : 'Wird geprüft...'}
          </span>
        </div>

        {queueStats && (
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-semibold text-yellow-600">{queueStats.pending}</p>
              <p className="text-xs text-slate-500">Ausstehend</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-blue-600">{queueStats.processing}</p>
              <p className="text-xs text-slate-500">In Bearbeitung</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-green-600">{queueStats.completed}</p>
              <p className="text-xs text-slate-500">Abgeschlossen</p>
            </div>
          </div>
        )}
      </div>

      {/* Data protection info */}
      <div className="card bg-slate-50">
        <h3 className="font-medium text-slate-800 mb-2">Datenschutz</h3>
        <ul className="text-sm text-slate-600 space-y-1">
          <li className="flex items-start">
            <svg className="w-4 h-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            Alle Daten werden lokal gespeichert (On-Premise)
          </li>
          <li className="flex items-start">
            <svg className="w-4 h-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            AES-256 Verschlüsselung für alle Aufnahmen
          </li>
          <li className="flex items-start">
            <svg className="w-4 h-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            90 Tage Aufbewahrungsfrist
          </li>
          <li className="flex items-start">
            <svg className="w-4 h-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            DSGVO-konform
          </li>
        </ul>
      </div>

      {/* Version info */}
      <div className="text-center text-sm text-slate-400">
        <p>VoxDocs v1.0.0</p>
        <p>Dental Speech-to-Text System</p>
      </div>
    </div>
  )
}
