import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import RecordButton from '../components/RecordButton'
import WaveformVisualizer from '../components/WaveformVisualizer'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { useAppStore } from '../stores/appStore'
import { syncService } from '../services/syncService'

interface UploadStatus {
  id: string
  duration: number
  status: 'uploading' | 'success' | 'offline' | 'error'
  uuid?: string
  error?: string
}

export default function RecordingPage() {
  const navigate = useNavigate()
  const { practiceId, selectedRoomId, rooms, processImmediately, pushToTalk, setPushToTalk } = useAppStore()
  const [uploads, setUploads] = useState<UploadStatus[]>([])
  const uploadIdCounter = useRef(0)

  const handleRecordingComplete = async (blob: Blob, duration: number, recordedAt: Date) => {
    // Create a unique ID for this upload
    const uploadId = `upload_${++uploadIdCounter.current}`

    // Add to uploads list immediately (non-blocking)
    setUploads(prev => [...prev, { id: uploadId, duration, status: 'uploading' }])

    // Upload in background - don't await, let it run async
    syncService.uploadRecording(
      blob,
      practiceId,
      selectedRoomId || undefined,
      processImmediately,
      recordedAt
    ).then(({ success, offline, result }) => {
      if (success) {
        const uuid = offline
          ? (result as { offlineId: string }).offlineId
          : (result as { uuid: string }).uuid
        setUploads(prev => prev.map(u =>
          u.id === uploadId
            ? { ...u, status: offline ? 'offline' : 'success', uuid }
            : u
        ))
      }
    }).catch((error) => {
      console.error('Upload failed:', error)
      setUploads(prev => prev.map(u =>
        u.id === uploadId
          ? { ...u, status: 'error', error: 'Upload fehlgeschlagen' }
          : u
      ))
    })
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

  const selectedRoom = rooms.find((r) => r.id === selectedRoomId)

  // Count uploads by status
  const uploadingCount = uploads.filter(u => u.status === 'uploading').length
  const successUploads = uploads.filter(u => u.status === 'success')
  const lastSuccess = successUploads[successUploads.length - 1]

  const clearUpload = (id: string) => {
    setUploads(prev => prev.filter(u => u.id !== id))
  }

  return (
    <div className="flex flex-col items-center space-y-8">
      {/* Room selector */}
      <div className="w-full">
        <label className="block text-sm font-medium text-slate-600 mb-2">
          Behandlungsraum
        </label>
        <select
          value={selectedRoomId || ''}
          onChange={(e) => useAppStore.getState().setSelectedRoom(Number(e.target.value) || null)}
          className="w-full p-3 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-dental-500 focus:border-dental-500"
        >
          <option value="">Raum auswählen...</option>
          {rooms.map((room) => (
            <option key={room.id} value={room.id}>
              {room.name}
            </option>
          ))}
        </select>
      </div>

      {/* Waveform visualization */}
      <div className="w-full relative">
        <WaveformVisualizer isRecording={isRecording} audioStream={audioStream} />
      </div>

      {/* Duration display */}
      <div className="text-center">
        <span className={`text-4xl font-mono ${isRecording ? 'text-red-600' : 'text-slate-400'}`}>
          {formatDuration(duration)}
        </span>
        {isRecording && (
          <p className="text-sm text-red-600 mt-2 animate-pulse">Aufnahme läuft...</p>
        )}
      </div>

      {/* Record button - NEVER disabled during upload */}
      <RecordButton
        isRecording={isRecording}
        onStart={startRecording}
        onStop={stopRecording}
        disabled={false}
        pushToTalk={pushToTalk}
      />

      {/* Push-to-talk toggle */}
      <div className="w-full flex items-center justify-between p-3 bg-slate-50 rounded-lg">
        <div className="flex items-center space-x-3">
          <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
          </svg>
          <div>
            <p className="text-sm font-medium text-slate-700">Push-to-Talk</p>
            <p className="text-xs text-slate-500">Gedrückt halten zum Aufnehmen</p>
          </div>
        </div>
        <button
          onClick={() => setPushToTalk(!pushToTalk)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            pushToTalk ? 'bg-dental-600' : 'bg-slate-300'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              pushToTalk ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Upload status indicator (non-blocking) */}
      {uploadingCount > 0 && (
        <div className="flex items-center space-x-2 text-dental-600 text-sm">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>{uploadingCount} Upload{uploadingCount > 1 ? 's' : ''} läuft...</span>
        </div>
      )}

      {recordingError && (
        <div className="text-red-600 text-center p-4 bg-red-50 rounded-lg w-full">
          {recordingError.message}
        </div>
      )}

      {/* Show last successful upload */}
      {lastSuccess && !isRecording && (
        <div className="w-full card">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-medium text-slate-800 mb-1">Letzte Aufnahme</h3>
              <p className="text-sm text-slate-600">
                Dauer: {formatDuration(lastSuccess.duration)}
              </p>
            </div>
            <button
              onClick={() => clearUpload(lastSuccess.id)}
              className="text-slate-400 hover:text-slate-600"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <button
            onClick={() => navigate(`/transcription/${lastSuccess.uuid}`)}
            className="btn btn-primary w-full mt-3"
          >
            Transkription ansehen
          </button>
        </div>
      )}

      {/* Show offline uploads */}
      {uploads.filter(u => u.status === 'offline').length > 0 && (
        <div className="w-full card border-yellow-300 bg-yellow-50">
          <h3 className="font-medium text-yellow-800 mb-2">
            {uploads.filter(u => u.status === 'offline').length} Aufnahme(n) offline gespeichert
          </h3>
          <p className="text-sm text-yellow-700">
            Werden automatisch hochgeladen sobald Verbindung besteht.
          </p>
        </div>
      )}

      {/* Quick info */}
      <div className="w-full text-center text-sm text-slate-500">
        <p>
          {selectedRoom
            ? `Aufnahme für ${selectedRoom.name}`
            : 'Bitte wählen Sie einen Behandlungsraum'}
        </p>
        <p className="mt-1">
          {processImmediately
            ? 'Sofortige Verarbeitung aktiviert'
            : 'Verarbeitung erfolgt über Nacht'}
        </p>
      </div>
    </div>
  )
}
