import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import RecordButton from '../components/RecordButton'
import WaveformVisualizer from '../components/WaveformVisualizer'
import CameraCapture from '../components/CameraCapture'
import { useAppStore } from '../stores/appStore'

interface AudioRecording {
  id: string
  blob: Blob
  duration: number
  recordedAt: Date
}

interface Photo {
  id: string
  blob: Blob
  url: string
  takenAt: Date
}

export default function NursingAppointmentPage() {
  const navigate = useNavigate()
  const { practiceId, pushToTalk, setPushToTalk } = useAppStore()

  const [appointmentUuid, setAppointmentUuid] = useState<string | null>(null)
  const [patientName, setPatientName] = useState('')
  const [audioRecordings, setAudioRecordings] = useState<AudioRecording[]>([])
  const [photos, setPhotos] = useState<Photo[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')

  const recordingIdCounter = useRef(0)

  // Create appointment on first action
  const ensureAppointmentCreated = async () => {
    if (appointmentUuid) return appointmentUuid

    try {
      const formData = new FormData()
      formData.append('practice_id', practiceId.toString())
      if (patientName) {
        formData.append('patient_name', patientName)
      }

      const response = await fetch('/api/appointments/create', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to create appointment')
      }

      const data = await response.json()
      setAppointmentUuid(data.uuid)
      return data.uuid
    } catch (error) {
      console.error('Error creating appointment:', error)
      alert('Fehler beim Erstellen des Termins')
      return null
    }
  }

  const handleRecordingComplete = async (blob: Blob, duration: number, recordedAt: Date) => {
    const recordingId = `recording_${++recordingIdCounter.current}`

    // Add to local list
    setAudioRecordings(prev => [
      ...prev,
      { id: recordingId, blob, duration, recordedAt }
    ])

    // Upload to server
    const uuid = await ensureAppointmentCreated()
    if (!uuid) return

    try {
      const formData = new FormData()
      formData.append('practice_id', practiceId.toString())
      formData.append('audio_file', blob, `recording_${recordingId}.webm`)

      const response = await fetch(`/api/appointments/${uuid}/upload-audio`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      console.log('Audio uploaded successfully')
    } catch (error) {
      console.error('Error uploading audio:', error)
      alert('Fehler beim Hochladen der Aufnahme')
    }
  }

  const handlePhotoCapture = async (photoBlob: Blob) => {
    const photoId = `photo_${Date.now()}`
    const photoUrl = URL.createObjectURL(photoBlob)

    // Add to local list
    const newPhoto = {
      id: photoId,
      blob: photoBlob,
      url: photoUrl,
      takenAt: new Date()
    }
    setPhotos(prev => [...prev, newPhoto])

    // Upload to server
    const uuid = await ensureAppointmentCreated()
    if (!uuid) return

    try {
      const formData = new FormData()
      formData.append('photo_file', photoBlob, `photo_${photoId}.jpg`)

      const response = await fetch(`/api/appointments/${uuid}/upload-photo`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      console.log('Photo uploaded successfully')
    } catch (error) {
      console.error('Error uploading photo:', error)
      alert('Fehler beim Hochladen des Fotos')
    }
  }

  const deleteAudio = (id: string) => {
    setAudioRecordings(prev => prev.filter(r => r.id !== id))
  }

  const deletePhoto = (id: string) => {
    setPhotos(prev => {
      const photo = prev.find(p => p.id === id)
      if (photo) {
        URL.revokeObjectURL(photo.url)
      }
      return prev.filter(p => p.id !== id)
    })
  }

  const completeAppointment = async () => {
    if (!appointmentUuid) {
      alert('Kein Termin erstellt')
      return
    }

    if (audioRecordings.length === 0) {
      alert('Bitte mindestens eine Audio-Aufnahme erstellen')
      return
    }

    setIsUploading(true)
    setUploadProgress('Termin wird abgeschlossen...')

    try {
      const response = await fetch(`/api/appointments/${appointmentUuid}/complete`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Failed to complete appointment')
      }

      setUploadProgress('Termin abgeschlossen! Die Transkription wird verarbeitet...')

      // Navigate to review page after a brief delay
      setTimeout(() => {
        navigate(`/appointment/${appointmentUuid}/review`)
      }, 2000)

    } catch (error) {
      console.error('Error completing appointment:', error)
      alert('Fehler beim Abschließen des Termins')
      setIsUploading(false)
    }
  }

  const {
    isRecording,
    duration,
    audioStream,
    startRecording,
    stopRecording,
    error: recordingError,
  } = useAudioRecorder({
    onRecordingComplete: handleRecordingComplete,
    onError: (err) => console.error('Recording error:', err),
  })

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="min-h-screen bg-slate-50 p-4 pb-32">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h1 className="text-2xl font-bold text-slate-800 mb-4">
            Neuer Pflegetermin
          </h1>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-2">
              Patient / Klient (optional)
            </label>
            <input
              type="text"
              value={patientName}
              onChange={(e) => setPatientName(e.target.value)}
              placeholder="Name eingeben..."
              className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 relative z-10"
              disabled={isRecording}
            />
          </div>
        </div>

        {/* Waveform visualization */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <WaveformVisualizer isRecording={isRecording} audioStream={audioStream} />

          {/* Duration display */}
          <div className="text-center mt-4">
            <span className={`text-3xl font-mono font-bold ${isRecording ? 'text-red-600' : 'text-slate-400'}`}>
              {formatDuration(duration)}
            </span>
            {isRecording && (
              <p className="text-sm text-red-600 mt-2 animate-pulse">Aufnahme läuft...</p>
            )}
          </div>

          {/* Record button */}
          <div className="mt-6 flex flex-col items-center">
            <RecordButton
              isRecording={isRecording}
              onStart={startRecording}
              onStop={stopRecording}
              disabled={false}
              pushToTalk={pushToTalk}
            />

            {/* Push-to-talk toggle */}
            <div className="w-full mt-4 flex items-center justify-between p-3 bg-slate-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-slate-700">Push-to-Talk</p>
                  <p className="text-xs text-slate-500">Gedrückt halten zum Aufnehmen</p>
                </div>
              </div>
              <button
                onClick={() => setPushToTalk(!pushToTalk)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${pushToTalk ? 'bg-primary-600' : 'bg-slate-300'
                  }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${pushToTalk ? 'translate-x-6' : 'translate-x-1'
                    }`}
                />
              </button>
            </div>
          </div>

          {recordingError && (
            <div className="mt-4 text-red-600 text-center p-3 bg-red-50 rounded-lg text-sm">
              {recordingError.message}
            </div>
          )}
        </div>

        {/* Audio recordings list */}
        {audioRecordings.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              Audio-Aufnahmen ({audioRecordings.length})
            </h2>
            <div className="space-y-3">
              {audioRecordings.map((recording, index) => (
                <div
                  key={recording.id}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="bg-primary-100 text-primary-600 p-2 rounded-lg">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">Aufnahme {index + 1}</p>
                      <p className="text-sm text-slate-600">
                        {formatDuration(recording.duration)} • {recording.recordedAt.toLocaleTimeString('de-DE')}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => deleteAudio(recording.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Camera */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">
            Fotos aufnehmen
          </h2>
          <CameraCapture onPhotoCapture={handlePhotoCapture} />
        </div>

        {/* Photos grid */}
        {photos.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">
              Fotos ({photos.length})
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {photos.map((photo) => (
                <div key={photo.id} className="relative group">
                  <img
                    src={photo.url}
                    alt={`Foto ${photos.indexOf(photo) + 1}`}
                    className="w-full h-32 object-cover rounded-lg"
                  />
                  <button
                    onClick={() => deletePhoto(photo.id)}
                    className="absolute top-2 right-2 p-2 bg-red-600 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload progress */}
        {isUploading && (
          <div className="bg-primary-50 border border-primary-200 rounded-lg p-4 text-center">
            <div className="flex items-center justify-center space-x-2 text-primary-700">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>{uploadProgress}</span>
            </div>
          </div>
        )}
      </div>

      {/* Fixed bottom button */}
      {(audioRecordings.length > 0 || photos.length > 0) && !isUploading && (
        <div className="fixed bottom-[60px] left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-lg z-40">
          <div className="max-w-2xl mx-auto">
            <button
              onClick={completeAppointment}
              disabled={audioRecordings.length === 0}
              className="btn btn-primary w-full text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Termin abschließen ({audioRecordings.length} Aufnahme{audioRecordings.length !== 1 ? 'n' : ''}, {photos.length} Foto{photos.length !== 1 ? 's' : ''})
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
