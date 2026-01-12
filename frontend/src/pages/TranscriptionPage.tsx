import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { transcriptionApi, classificationApi } from '../services/api'

interface Segment {
  start: number
  end: number
  text: string
  confidence: number | null
}

interface TaskData {
  id: number
  description: string
  priority: string
  status: string
  due_date: string | null
  tooth_reference: string | null
  category: string | null
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
  corrected_text: string | null
  summary: string | null
  language: string
  processing_time: number | null
  confidence: number | null
  segments: Segment[]
  tasks: TaskData[]
  correction_count: number
  llm_processed: boolean
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
  const [activeTab, setActiveTab] = useState<'text' | 'tasks' | 'segments' | 'analysis'>('text')
  const [showOriginal, setShowOriginal] = useState(false)

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

      {/* Summary card - shown if LLM processed */}
      {transcription.summary && (
        <div className="card bg-dental-50 border-dental-200">
          <div className="flex items-start space-x-3">
            <svg className="w-5 h-5 text-dental-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div>
              <h3 className="font-medium text-dental-800 text-sm">Zusammenfassung</h3>
              <p className="text-dental-700 text-sm mt-1">{transcription.summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab navigation */}
      <div className="flex space-x-1 bg-slate-100 p-1 rounded-lg">
        {(['text', 'tasks', 'segments', 'analysis'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-white text-dental-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {tab === 'text' ? 'Text' : tab === 'tasks' ? `Aufgaben${transcription.tasks.length > 0 ? ` (${transcription.tasks.length})` : ''}` : tab === 'segments' ? 'Segmente' : 'Verbrauch'}
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
              {/* Toggle for corrected/original text */}
              {transcription.corrected_text && (
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-medium text-dental-600 bg-dental-100 px-2 py-1 rounded">
                      KI-korrigiert
                    </span>
                  </div>
                  <button
                    onClick={() => setShowOriginal(!showOriginal)}
                    className="text-sm text-slate-500 hover:text-slate-700"
                  >
                    {showOriginal ? 'Korrektur anzeigen' : 'Original anzeigen'}
                  </button>
                </div>
              )}
              <p className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                {showOriginal || !transcription.corrected_text
                  ? transcription.full_text
                  : transcription.corrected_text}
              </p>
              <button
                onClick={() => setIsEditing(true)}
                className="btn btn-secondary mt-4 w-full"
              >
                Manuell korrigieren
              </button>
            </>
          )}
        </div>
      )}

      {/* Tasks tab */}
      {activeTab === 'tasks' && (
        <div className="space-y-3">
          {transcription.tasks.length === 0 ? (
            <div className="card text-center py-8">
              <svg className="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              <p className="text-slate-500">Keine Aufgaben erkannt</p>
              <p className="text-slate-400 text-sm mt-1">
                {transcription.llm_processed
                  ? 'In dieser Aufnahme wurden keine Aufgaben gefunden.'
                  : 'Die KI-Analyse wurde noch nicht durchgeführt.'}
              </p>
            </div>
          ) : (
            transcription.tasks.map((task) => (
              <div key={task.id} className="card">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        task.priority === 'hoch'
                          ? 'bg-red-100 text-red-700'
                          : task.priority === 'mittel'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {task.priority === 'hoch' ? 'Hoch' : task.priority === 'mittel' ? 'Mittel' : 'Niedrig'}
                      </span>
                      {task.tooth_reference && (
                        <span className="text-xs text-slate-500">{task.tooth_reference}</span>
                      )}
                    </div>
                    <p className="text-slate-800">{task.description}</p>
                    {task.due_date && (
                      <p className="text-sm text-slate-500 mt-2">
                        <span className="font-medium">Fällig:</span> {task.due_date}
                      </p>
                    )}
                  </div>
                  <div className={`ml-3 px-2 py-1 rounded text-xs ${
                    task.status === 'completed'
                      ? 'bg-green-100 text-green-700'
                      : task.status === 'in_progress'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {task.status === 'completed' ? 'Erledigt' : task.status === 'in_progress' ? 'In Bearbeitung' : 'Offen'}
                  </div>
                </div>
              </div>
            ))
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

      {activeTab === 'analysis' && (
        <div className="space-y-6">
          {/* Verbrauch/Billing info */}
          <div className="card bg-blue-50 border-blue-200">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <div>
                <h3 className="font-medium text-blue-800 text-sm">Abrechnungsrelevante Positionen</h3>
                <p className="text-blue-700 text-xs mt-1">Erkannte Tätigkeiten und Materialien für die Abrechnung</p>
              </div>
            </div>
          </div>

          {/* Tätigkeiten / Activities */}
          <div className="card">
            <h3 className="font-medium text-green-700 mb-3 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Tätigkeiten
            </h3>
            {classifications?.summary.treatments && classifications.summary.treatments.length > 0 ? (
              <ul className="space-y-2">
                {classifications.summary.treatments.map((t, i) => (
                  <li key={i} className="flex items-start py-2 border-b border-slate-100 last:border-0">
                    <span className="w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-medium mr-3 flex-shrink-0">
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-slate-800">{t.text}</p>
                      {t.tooth && <p className="text-sm text-slate-500">Zahn {t.tooth}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-400 text-sm">Keine Tätigkeiten erkannt</p>
            )}
          </div>

          {/* Materialverbrauch / Materials */}
          <div className="card">
            <h3 className="font-medium text-blue-700 mb-3 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
              Materialverbrauch
            </h3>
            {classifications?.classifications.filter(c => c.category === 'material').length > 0 ? (
              <ul className="space-y-2">
                {classifications.classifications
                  .filter(c => c.category === 'material')
                  .map((m, i) => (
                    <li key={i} className="flex items-center py-2 border-b border-slate-100 last:border-0">
                      <span className="w-2 h-2 rounded-full bg-blue-500 mr-3 flex-shrink-0"></span>
                      <span className="text-slate-800">{m.extracted_text}</span>
                      {m.tooth_number && <span className="text-sm text-slate-500 ml-2">(Zahn {m.tooth_number})</span>}
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="text-slate-400 text-sm">Kein Materialverbrauch erkannt</p>
            )}
          </div>

          {/* Beteiligte Zähne */}
          {classifications?.summary.teeth_mentioned && classifications.summary.teeth_mentioned.length > 0 && (
            <div className="card">
              <h3 className="font-medium text-yellow-700 mb-3 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                </svg>
                Beteiligte Zähne
              </h3>
              <div className="flex flex-wrap gap-2">
                {classifications.summary.teeth_mentioned.map((tooth) => (
                  <span key={tooth} className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                    {tooth}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Befunde/Diagnosen - relevant for billing codes */}
          {classifications?.summary.diagnoses && classifications.summary.diagnoses.length > 0 && (
            <div className="card">
              <h3 className="font-medium text-red-700 mb-3 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Befunde / Diagnosen
              </h3>
              <ul className="space-y-2">
                {classifications.summary.diagnoses.map((d, i) => (
                  <li key={i} className="flex items-start py-2 border-b border-slate-100 last:border-0">
                    <span className="w-2 h-2 rounded-full bg-red-500 mr-3 mt-2 flex-shrink-0"></span>
                    <div>
                      <p className="text-slate-800">{d.text}</p>
                      {d.tooth && <p className="text-sm text-slate-500">Zahn {d.tooth}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Empty state */}
          {(!classifications ||
            ((!classifications.summary.treatments || classifications.summary.treatments.length === 0) &&
             classifications.classifications.filter(c => c.category === 'material').length === 0)) && (
            <div className="card text-center py-8">
              <svg className="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p className="text-slate-500">Keine abrechnungsrelevanten Positionen erkannt</p>
              <p className="text-slate-400 text-sm mt-1">
                {transcription.llm_processed
                  ? 'Die KI hat keine Tätigkeiten oder Materialien in dieser Aufnahme gefunden.'
                  : 'Die KI-Analyse wurde noch nicht durchgeführt.'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Processing info */}
      <div className="text-center text-sm text-slate-500 space-y-1">
        <p>Sprache: {transcription.language.toUpperCase()}</p>
        {transcription.processing_time && (
          <p>Verarbeitungszeit: {transcription.processing_time.toFixed(1)}s</p>
        )}
        <p className="flex items-center justify-center space-x-2">
          <span>KI-Analyse:</span>
          {transcription.llm_processed ? (
            <span className="text-green-600 flex items-center">
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Abgeschlossen
            </span>
          ) : (
            <span className="text-slate-400">Nicht verfügbar</span>
          )}
        </p>
      </div>
    </div>
  )
}
