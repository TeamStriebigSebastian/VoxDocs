import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { audioApi } from '../services/api'

interface Recording {
  id: number
  uuid: string
  status: string
  duration_seconds: number | null
  recorded_at: string
  has_transcription: boolean
}

export default function RecordingsListPage() {
  const navigate = useNavigate()
  const { practiceId } = useAppStore()
  const [recordings, setRecordings] = useState<Recording[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRecordings()
  }, [practiceId])

  const loadRecordings = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await audioApi.list(practiceId)
      setRecordings(response.recordings)
    } catch (err) {
      setError('Aufnahmen konnten nicht geladen werden')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (dateString: string): string => {
    // Backend sends UTC times without 'Z' suffix - add it for proper parsing
    let date: Date
    if (dateString.includes('Z') || dateString.includes('+')) {
      date = new Date(dateString)
    } else {
      // Assume UTC if no timezone specified
      date = new Date(dateString + 'Z')
    }
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      queued: 'bg-blue-100 text-blue-800',
      processing: 'bg-purple-100 text-purple-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    }

    const labels: Record<string, string> = {
      pending: 'Ausstehend',
      queued: 'In Warteschlange',
      processing: 'Wird verarbeitet',
      completed: 'Abgeschlossen',
      failed: 'Fehlgeschlagen',
    }

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-slate-100 text-slate-800'}`}>
        {labels[status] || status}
      </span>
    )
  }

  const handleDelete = async (uuid: string) => {
    if (!confirm('Aufnahme wirklich löschen?')) return

    try {
      await audioApi.delete(uuid)
      setRecordings(recordings.filter((r) => r.uuid !== uuid))
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-dental-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={loadRecordings} className="btn btn-primary">
          Erneut versuchen
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-slate-800">Aufnahmen</h2>
        <button onClick={loadRecordings} className="btn btn-secondary text-sm">
          Aktualisieren
        </button>
      </div>

      {recordings.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
          <p>Noch keine Aufnahmen vorhanden</p>
          <button onClick={() => navigate('/')} className="btn btn-primary mt-4">
            Erste Aufnahme starten
          </button>
        </div>
      ) : (
        <ul className="space-y-3">
          {recordings.map((recording) => (
            <li key={recording.uuid} className="card">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    {getStatusBadge(recording.status)}
                    <span className="text-sm text-slate-500">
                      {formatDuration(recording.duration_seconds)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 truncate">
                    {formatDate(recording.recorded_at)}
                  </p>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {recording.status === 'completed' && (
                    <button
                      onClick={() => navigate(`/transcription/${recording.uuid}`)}
                      className="p-2 text-dental-600 hover:bg-dental-50 rounded-lg transition-colors"
                      title="Transkription ansehen"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(recording.uuid)}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Löschen"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
