import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

interface Photo {
  uuid: string
  caption: string | null
  taken_at: string
}

interface AudioRecording {
  uuid: string
  duration: number | null
  recorded_at: string
}

interface Transcription {
  status: 'pending' | 'processing' | 'ready' | 'confirmed' | 'error'
  full_text: string | null
  translated_text: string | null
  original_language: string | null
  summary: string | null
  services: string | null
  observations: string | null
  next_tasks: string | null
  tts_audio_url: string | null
  confirmed_at: string | null
}

const getLanguageName = (code: string | null) => {
  if (!code) return 'Unbekannt';
  const languages: Record<string, string> = {
    'de': 'Deutsch',
    'en': 'Englisch',
    'pl': 'Polnisch',
    'ro': 'Rumänisch',
    'tr': 'Türkisch',
    'ru': 'Russisch',
    'ar': 'Arabisch',
    'fr': 'Französisch',
    'es': 'Spanisch',
    'it': 'Italienisch'
  };
  return languages[code] || code;
};

interface Appointment {
  uuid: string
  patient_name: string | null
  started_at: string
  completed_at: string | null
  status: string
  audio_recordings: AudioRecording[]
  photos: Photo[]
  transcription: Transcription | null
}

export default function AppointmentReviewPage() {
  const { appointmentUuid } = useParams<{ appointmentUuid: string }>()
  const navigate = useNavigate()

  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    summary: '',
    services: '',
    observations: '',
    next_tasks: ''
  })

  const audioRef = useRef<HTMLAudioElement>(null)

  // Load appointment data
  useEffect(() => {
    loadAppointment()
  }, [appointmentUuid])

  const loadAppointment = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/appointments/${appointmentUuid}`)

      if (!response.ok) {
        throw new Error('Termin nicht gefunden')
      }

      const data = await response.json()
      setAppointment(data)
      if (data.transcription) {
        setEditForm({
          summary: data.transcription.summary || '',
          services: data.transcription.services || '',
          observations: data.transcription.observations || '',
          next_tasks: data.transcription.next_tasks || ''
        })
      }
      setError(null)
    } catch (err) {
      console.error('Error loading appointment:', err)
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  const handlePlayTTS = () => {
    if (!audioRef.current) return

    const playPromise = audioRef.current.play()
    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          setIsPlaying(true)
        })
        .catch(error => {
          console.error("Playback failed:", error)
          setIsPlaying(false)
          // Don't alert on abort (user clicked pause/stop)
          if (error.name !== 'AbortError') {
            alert(`Wiedergabe fehlgeschlagen: ${error.message}`)
          }
        })
    }
  }

  const handlePauseTTS = () => {
    if (!audioRef.current) return
    audioRef.current.pause()
    setIsPlaying(false)
  }

  const handleStopTTS = () => {
    if (!audioRef.current) return
    audioRef.current.pause()
    audioRef.current.currentTime = 0
    setIsPlaying(false)
  }

  const handleAudioError = (e: any) => {
    console.error("Audio error:", e)
    setIsPlaying(false)
    alert("Audio konnte nicht geladen werden.")
  }

  const handleSave = async () => {
    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('summary', editForm.summary)
      formData.append('services', editForm.services)
      formData.append('observations', editForm.observations)
      formData.append('next_tasks', editForm.next_tasks)

      const response = await fetch(`/api/appointments/${appointmentUuid}/transcription`, {
        method: 'PUT',
        body: formData,
      })

      if (!response.ok) throw new Error('Update failed')

      await loadAppointment()
      setIsEditing(false)
    } catch (err) {
      console.error('Error updating:', err)
      alert('Fehler beim Speichern')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!appointment) return
    if (isEditing) {
      alert('Bitte zuerst die Änderungen speichern.')
      return
    }
    // In a real app, you'd get the caregiver name from auth
    const caregiverName = prompt('Bitte Ihren Namen zur Bestätigung eingeben:')
    if (!caregiverName) return

    setConfirming(true)

    try {
      const formData = new FormData()
      formData.append('confirmed_by', caregiverName)

      const response = await fetch(`/api/appointments/${appointmentUuid}/confirm`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Bestätigung fehlgeschlagen')
      }

      // Reload to show confirmed status
      await loadAppointment()

      alert('Dokumentation erfolgreich bestätigt!')
      navigate('/appointments')
    } catch (err) {
      console.error('Error confirming:', err)
      alert('Fehler bei der Bestätigung')
    } finally {
      setConfirming(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Lade Termin...</p>
        </div>
      </div>
    )
  }

  if (error || !appointment) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <svg className="w-12 h-12 text-red-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-red-800 font-medium">{error || 'Termin nicht gefunden'}</p>
            <button
              onClick={() => navigate('/appointments')}
              className="mt-4 btn bg-slate-200 hover:bg-slate-300 text-slate-800"
            >
              Zurück zur Übersicht
            </button>
          </div>
        </div>
      </div>
    )
  }

  const transcription = appointment.transcription

  return (
    <div className="min-h-screen bg-slate-50 p-4 pb-32">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-slate-800">Eintrag prüfen</h1>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${appointment.status === 'confirmed'
              ? 'bg-green-100 text-green-800'
              : appointment.status === 'completed'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-yellow-100 text-yellow-800'
              }`}>
              {appointment.status === 'confirmed' ? 'Bestätigt' : appointment.status === 'completed' ? 'Abgeschlossen' : 'In Bearbeitung'}
            </span>
          </div>
          {appointment.patient_name && (
            <div className="flex items-center space-x-2 text-slate-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-medium">{appointment.patient_name}</span>
            </div>
          )}
          <div className="mt-2 text-sm text-slate-500">
            {new Date(appointment.started_at).toLocaleString('de-DE')}
          </div>
        </div>

        {/* Transcription Status */}
        {transcription && transcription.status === 'pending' && (
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-center">
            <div className="flex items-center justify-center space-x-3 text-slate-700">
              <span className="animate-pulse h-3 w-3 bg-slate-400 rounded-full"></span>
              <span className="font-medium">Aufnahme eingereiht...</span>
            </div>
            <p className="mt-2 text-sm text-slate-600">Warten auf freien Verarbeitungsslot.</p>
          </div>
        )}

        {transcription && transcription.status === 'processing' && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
            <div className="flex items-center justify-center space-x-3 text-blue-700">
              <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="font-medium">Transkription wird verarbeitet...</span>
            </div>
            <p className="mt-2 text-sm text-blue-600">Sie werden benachrichtigt, wenn die Dokumentation fertig ist.</p>
          </div>
        )}

        {transcription && transcription.status === 'error' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-center space-x-2 text-red-700">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">Fehler bei der Transkription</span>
            </div>
            <p className="mt-2 text-sm text-red-600">Bitte kontaktieren Sie den Support.</p>
          </div>
        )}

        {transcription && !['pending', 'processing', 'ready', 'confirmed', 'error'].includes(transcription.status) && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
            <p className="text-amber-800 font-mono">Unknown Status: {transcription.status}</p>
          </div>
        )}

        {/* TTS Audio Player */}
        {transcription && transcription.status === 'ready' && transcription.tts_audio_url && (
          <div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-primary-900">Dokumentation anhören</h2>
              <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            </div>

            <audio
              ref={audioRef}
              src={transcription.tts_audio_url}
              onEnded={() => setIsPlaying(false)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onError={handleAudioError}
              preload="auto"
              className="hidden"
            />

            <div className="flex space-x-2">
              {!isPlaying ? (
                <button
                  onClick={handlePlayTTS}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center space-x-2 transition-colors shadow-sm"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                  </svg>
                  <span>Abspielen</span>
                </button>
              ) : (
                <button
                  onClick={handlePauseTTS}
                  className="flex-1 bg-amber-500 hover:bg-amber-600 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center space-x-2 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Pause</span>
                </button>
              )}

              <button
                onClick={handleStopTTS}
                className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors"
                title="Stopp"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
              </button>
            </div>

            <p className="mt-3 text-center text-sm text-primary-700">
              Die Dokumentation wird vorgelesen mit den Kategorien
            </p>
          </div>
        )}

        {/* Global Edit Button */}
        {transcription && transcription.status === 'ready' && !transcription.confirmed_at && (
          <div className="flex justify-end">
            {!isEditing ? (
              <button
                onClick={() => setIsEditing(true)}
                className="btn bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 flex items-center space-x-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span>Inhalte bearbeiten</span>
              </button>
            ) : (
              <div className="flex space-x-2">
                <button
                  onClick={() => setIsEditing(false)}
                  className="btn bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  Abbrechen
                </button>
                <button
                  onClick={handleSave}
                  className="btn bg-primary-600 text-white hover:bg-primary-700"
                >
                  Speichern
                </button>
              </div>
            )}
          </div>
        )}

        {/* Transcription Categories */}
        {transcription && transcription.status === 'ready' && (
          <div className="space-y-4">

            {/* Original & Translation */}
            {transcription.full_text && (
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                  <h3 className="font-semibold text-slate-800 flex items-center space-x-2">
                    <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                    </svg>
                    <span>Transkription</span>
                  </h3>
                  {transcription.original_language && (
                    <span className="text-xs font-medium px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                      Sprache: {getLanguageName(transcription.original_language)}
                    </span>
                  )}
                </div>

                <div className="p-6 space-y-6">
                  {/* Original */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Original-Audio Transkript</h4>
                    <p className="text-slate-600 whitespace-pre-wrap text-sm font-mono bg-slate-50 p-3 rounded border border-slate-100">
                      {transcription.full_text}
                    </p>
                  </div>

                  {/* Translation (if available and different, or if forced) */}
                  {transcription.translated_text && transcription.translated_text !== transcription.full_text && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Deutsche Übersetzung</h4>
                      <p className="text-slate-800 whitespace-pre-wrap text-sm bg-yellow-50 p-3 rounded border border-yellow-100">
                        {transcription.translated_text}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Zusammenfassung */}
            {/* Zusammenfassung */}
            {(transcription.summary || isEditing) && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-start space-x-3">
                  <div className="bg-blue-100 text-blue-600 p-2 rounded-lg">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800 mb-2">Zusammenfassung</h3>
                    {isEditing ? (
                      <textarea
                        className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={4}
                        value={editForm.summary}
                        onChange={(e) => setEditForm({ ...editForm, summary: e.target.value })}
                      />
                    ) : (
                      <p className="text-slate-600 whitespace-pre-wrap">{transcription.summary}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Erbrachte Leistungen */}
            {/* Erbrachte Leistungen */}
            {(transcription.services || isEditing) && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-start space-x-3">
                  <div className="bg-green-100 text-green-600 p-2 rounded-lg">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800 mb-2">Erbrachte Leistungen</h3>
                    {isEditing ? (
                      <textarea
                        className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-transparent"
                        rows={4}
                        value={editForm.services}
                        onChange={(e) => setEditForm({ ...editForm, services: e.target.value })}
                      />
                    ) : (
                      <p className="text-slate-600 whitespace-pre-wrap">{transcription.services}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Besonderheiten */}
            {/* Besonderheiten */}
            {(transcription.observations || isEditing) && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-start space-x-3">
                  <div className="bg-yellow-100 text-yellow-600 p-2 rounded-lg">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800 mb-2">Besonderheiten</h3>
                    {isEditing ? (
                      <textarea
                        className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                        rows={4}
                        value={editForm.observations}
                        onChange={(e) => setEditForm({ ...editForm, observations: e.target.value })}
                      />
                    ) : (
                      <p className="text-slate-600 whitespace-pre-wrap">{transcription.observations}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Aufgaben für nächsten Termin */}
            {/* Aufgaben für nächsten Termin */}
            {(transcription.next_tasks || isEditing) && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-start space-x-3">
                  <div className="bg-purple-100 text-purple-600 p-2 rounded-lg">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-slate-800 mb-2">Aufgaben für nächsten Termin</h3>
                    {isEditing ? (
                      <textarea
                        className="w-full p-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        rows={4}
                        value={editForm.next_tasks}
                        onChange={(e) => setEditForm({ ...editForm, next_tasks: e.target.value })}
                      />
                    ) : (
                      <p className="text-slate-600 whitespace-pre-wrap">{transcription.next_tasks}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Photo Gallery */}
        {appointment.photos.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              Fotos ({appointment.photos.length})
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {appointment.photos.map((photo) => (
                <div key={photo.uuid} className="relative">
                  <img
                    src={`/api/appointments/${appointmentUuid}/photos/${photo.uuid}`}
                    alt={photo.caption || 'Pflegefoto'}
                    className="w-full h-32 object-cover rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => window.open(`/api/appointments/${appointmentUuid}/photos/${photo.uuid}`, '_blank')}
                  />
                  {photo.caption && (
                    <p className="mt-1 text-xs text-slate-600 line-clamp-2">{photo.caption}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recording Info */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">
            Audio-Aufnahmen ({appointment.audio_recordings.length})
          </h3>
          <div className="space-y-2">
            {appointment.audio_recordings.map((recording, index) => (
              <div key={recording.uuid} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="bg-slate-200 p-2 rounded-lg">
                    <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800">Aufnahme {index + 1}</p>
                    <p className="text-xs text-slate-500">
                      {recording.duration ? `${Math.round(recording.duration)}s` : 'Dauer unbekannt'} • {new Date(recording.recorded_at).toLocaleTimeString('de-DE')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Fixed bottom confirm button */}
      {transcription && transcription.status === 'ready' && !transcription.confirmed_at && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-lg mb-20 z-10">
          <div className="max-w-3xl mx-auto">
            <button
              onClick={handleConfirm}
              disabled={confirming}
              className="btn btn-primary w-full text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {confirming ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Wird bestätigt...</span>
                </>
              ) : (
                <>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Doku Bestätigen</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Confirmed status */}
      {transcription && transcription.confirmed_at && (
        <div className="fixed bottom-0 left-0 right-0 bg-green-50 border-t border-green-200 p-4">
          <div className="max-w-3xl mx-auto text-center">
            <div className="flex items-center justify-center space-x-2 text-green-700">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">
                Dokumentation bestätigt am {new Date(transcription.confirmed_at).toLocaleString('de-DE')}
              </span>
            </div>
            <button
              onClick={() => navigate('/appointments')}
              className="mt-3 btn bg-white hover:bg-slate-50 text-slate-700 border border-slate-300"
            >
              Zurück zur Übersicht
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
