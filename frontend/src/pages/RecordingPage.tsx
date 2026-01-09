import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import RecordButton from '../components/RecordButton'
import WaveformVisualizer from '../components/WaveformVisualizer'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { useAppStore } from '../stores/appStore'
import { audioApi } from '../services/api'

export default function RecordingPage() {
  const navigate = useNavigate()
  const { practiceId, selectedRoomId, rooms, processImmediately } = useAppStore()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [lastUpload, setLastUpload] = useState<{ uuid: string; duration: number } | null>(null)

  const handleRecordingComplete = async (blob: Blob, duration: number) => {
    setIsUploading(true)
    setUploadError(null)

    try {
      const result = await audioApi.upload(blob, practiceId, selectedRoomId || undefined, processImmediately)
      setLastUpload({ uuid: result.uuid, duration })
    } catch (error) {
      console.error('Upload failed:', error)
      setUploadError('Upload fehlgeschlagen. Bitte erneut versuchen.')
    } finally {
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
    onError: (err) => setUploadError(err.message),
  })

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const selectedRoom = rooms.find((r) => r.id === selectedRoomId)

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

      {/* Record button */}
      <RecordButton
        isRecording={isRecording}
        onStart={startRecording}
        onStop={stopRecording}
        disabled={isUploading}
      />

      {/* Status messages */}
      {isUploading && (
        <div className="flex items-center space-x-2 text-dental-600">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Wird hochgeladen...</span>
        </div>
      )}

      {uploadError && (
        <div className="text-red-600 text-center p-4 bg-red-50 rounded-lg">
          {uploadError}
        </div>
      )}

      {recordingError && (
        <div className="text-red-600 text-center p-4 bg-red-50 rounded-lg">
          {recordingError.message}
        </div>
      )}

      {lastUpload && !isRecording && !isUploading && (
        <div className="w-full card">
          <h3 className="font-medium text-slate-800 mb-2">Letzte Aufnahme</h3>
          <p className="text-sm text-slate-600 mb-3">
            Dauer: {formatDuration(lastUpload.duration)}
          </p>
          <div className="flex space-x-2">
            <button
              onClick={() => navigate(`/transcription/${lastUpload.uuid}`)}
              className="btn btn-primary flex-1"
            >
              Transkription ansehen
            </button>
            <button
              onClick={() => setLastUpload(null)}
              className="btn btn-secondary"
            >
              Schließen
            </button>
          </div>
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
