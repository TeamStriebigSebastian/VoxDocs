import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { transcriptionApi, classificationApi } from '../services/api'

interface Segment {
  start: number
  end: number
  text: string
  confidence: number | null
}

interface Classification {
  category: string
  extracted_text: string
  normalized_value: string | null
  confidence: number
  tooth_number: string | null
  surface: string | null
}

interface TranscriptionData {
  full_text: string
  language: string
  processing_time: number | null
  confidence: number | null
  segments: Segment[]
  correction_count: number
}

interface ClassificationData {
  total_entities: number
  classifications: Classification[]
  summary: {
    teeth_mentioned: string[]
    diagnoses: Array<{ text: string; tooth: string | null }>
    treatments: Array<{ text: string; tooth: string | null }>
    findings: Array<{ text: string; tooth: string | null }>
  }
}

export default function TranscriptionPage() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()
  const [transcription, setTranscription] = useState<TranscriptionData | null>(null)
  const [classifications, setClassifications] = useState<ClassificationData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState('')
  const [activeTab, setActiveTab] = useState<'text' | 'segments' | 'analysis'>('text')

  useEffect(() => {
    if (uuid) {
      loadData()
    }
  }, [uuid])

  const loadData = async () => {
    if (!uuid) return

    setIsLoading(true)
    setError(null)

    try {
      const [transcriptionData, classificationData] = await Promise.all([
        transcriptionApi.get(uuid),
        classificationApi.get(uuid).catch(() => null),
      ])

      setTranscription(transcriptionData)
      setClassifications(classificationData)
      setEditedText(transcriptionData.full_text)
    } catch (err) {
      setError('Transkription konnte nicht geladen werden')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveCorrection = async () => {
    if (!uuid || !transcription) return

    try {
      await transcriptionApi.correct(uuid, editedText)
      setTranscription({ ...transcription, full_text: editedText, correction_count: transcription.correction_count + 1 })
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to save correction:', err)
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      finding: 'bg-orange-100 text-orange-800',
      diagnosis: 'bg-red-100 text-red-800',
      treatment: 'bg-green-100 text-green-800',
      material: 'bg-blue-100 text-blue-800',
      instrument: 'bg-purple-100 text-purple-800',
      anatomy: 'bg-pink-100 text-pink-800',
      tooth: 'bg-yellow-100 text-yellow-800',
      surface: 'bg-cyan-100 text-cyan-800',
    }
    return colors[category] || 'bg-slate-100 text-slate-800'
  }

  const getCategoryLabel = (category: string): string => {
    const labels: Record<string, string> = {
      finding: 'Befund',
      diagnosis: 'Diagnose',
      treatment: 'Behandlung',
      material: 'Material',
      instrument: 'Instrument',
      anatomy: 'Anatomie',
      tooth: 'Zahn',
      surface: 'Fläche',
    }
    return labels[category] || category
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-dental-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error || !transcription) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error || 'Transkription nicht gefunden'}</p>
        <button onClick={() => navigate('/recordings')} className="btn btn-primary">
          Zurück zu Aufnahmen
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={() => navigate('/recordings')} className="text-dental-600 flex items-center">
          <svg className="w-5 h-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Zurück
        </button>
        {transcription.correction_count > 0 && (
          <span className="text-sm text-slate-500">
            {transcription.correction_count} Korrektur(en)
          </span>
        )}
      </div>

      {/* Tab navigation */}
      <div className="flex space-x-1 bg-slate-100 p-1 rounded-lg">
        {(['text', 'segments', 'analysis'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-white text-dental-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab === 'text' ? 'Text' : tab === 'segments' ? 'Segmente' : 'Analyse'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'text' && (
        <div className="card">
          {isEditing ? (
            <>
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                className="w-full h-64 p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-dental-500 focus:border-dental-500"
              />
              <div className="flex space-x-2 mt-4">
                <button onClick={handleSaveCorrection} className="btn btn-primary flex-1">
                  Speichern
                </button>
                <button
                  onClick={() => {
                    setEditedText(transcription.full_text)
                    setIsEditing(false)
                  }}
                  className="btn btn-secondary"
                >
                  Abbrechen
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                {transcription.full_text}
              </p>
              <button
                onClick={() => setIsEditing(true)}
                className="btn btn-secondary mt-4 w-full"
              >
                Korrigieren
              </button>
            </>
          )}
        </div>
      )}

      {activeTab === 'segments' && (
        <div className="space-y-2">
          {transcription.segments.map((segment, index) => (
            <div key={index} className="card py-3">
              <div className="flex items-start space-x-3">
                <span className="text-xs text-slate-400 font-mono w-20 flex-shrink-0">
                  {formatTime(segment.start)} - {formatTime(segment.end)}
                </span>
                <p className="text-slate-800 flex-1">{segment.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'analysis' && classifications && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="card">
            <h3 className="font-medium text-slate-800 mb-3">Zusammenfassung</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Zähne erwähnt:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {classifications.summary.teeth_mentioned.map((tooth) => (
                    <span key={tooth} className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                      {tooth}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-slate-500">Entitäten:</span>
                <p className="font-medium">{classifications.total_entities}</p>
              </div>
            </div>
          </div>

          {/* Classifications list */}
          <div className="card">
            <h3 className="font-medium text-slate-800 mb-3">Erkannte Elemente</h3>
            <div className="space-y-2">
              {classifications.classifications.map((c, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(c.category)}`}>
                      {getCategoryLabel(c.category)}
                    </span>
                    <span className="text-slate-800">{c.extracted_text}</span>
                  </div>
                  {c.tooth_number && (
                    <span className="text-sm text-slate-500">Zahn {c.tooth_number}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Diagnoses */}
          {classifications.summary.diagnoses.length > 0 && (
            <div className="card">
              <h3 className="font-medium text-red-700 mb-3">Diagnosen</h3>
              <ul className="space-y-1">
                {classifications.summary.diagnoses.map((d, i) => (
                  <li key={i} className="text-slate-700">
                    {d.text} {d.tooth && <span className="text-slate-500">(Zahn {d.tooth})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Treatments */}
          {classifications.summary.treatments.length > 0 && (
            <div className="card">
              <h3 className="font-medium text-green-700 mb-3">Behandlungen</h3>
              <ul className="space-y-1">
                {classifications.summary.treatments.map((t, i) => (
                  <li key={i} className="text-slate-700">
                    {t.text} {t.tooth && <span className="text-slate-500">(Zahn {t.tooth})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Processing info */}
      <div className="text-center text-sm text-slate-500">
        <p>Sprache: {transcription.language.toUpperCase()}</p>
        {transcription.processing_time && (
          <p>Verarbeitungszeit: {transcription.processing_time.toFixed(1)}s</p>
        )}
      </div>
    </div>
  )
}
