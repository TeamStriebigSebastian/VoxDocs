import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { onboardingApi } from '../services/api'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { syncService } from '../services/syncService'

interface Category {
  category: string
  total_phrases: number
  completed_phrases: number
  phrases: Array<{
    phrase_index: number
    phrase_text: string
    is_recorded: boolean
  }>
}

export default function OnboardingPage() {
  const { practiceId, userId } = useAppStore()
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [currentCategoryIndex, setCurrentCategoryIndex] = useState(0)
  const [currentPhraseIndex, setCurrentPhraseIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState({ completed: 0, total: 0 })
  const [speakerName, setSpeakerName] = useState('')
  const [speakerNotes, setSpeakerNotes] = useState('')
  const [offlineCount, setOfflineCount] = useState(0)

  const currentCategory = categories[currentCategoryIndex]
  const currentPhrase = currentCategory?.phrases[currentPhraseIndex]

  const handleRecordingComplete = async (blob: Blob) => {
    if (!sessionId || !currentCategory || !currentPhrase) return

    try {
      const { success, offline } = await syncService.uploadPhrase(
        sessionId,
        blob,
        currentCategory.category,
        currentPhrase.phrase_index,
        currentPhrase.phrase_text
      )

      if (success) {
        // Update local state
        const updatedCategories = [...categories]
        updatedCategories[currentCategoryIndex].phrases[currentPhraseIndex].is_recorded = true
        updatedCategories[currentCategoryIndex].completed_phrases += 1
        setCategories(updatedCategories)

        setProgress((prev) => ({ ...prev, completed: prev.completed + 1 }))

        if (offline) {
          setOfflineCount(prev => prev + 1)
        }

        // Move to next phrase
        moveToNext()
      }
    } catch (err) {
      console.error('Failed to save phrase recording:', err)
    }
  }

  const { isRecording, startRecording, stopRecording, duration } = useAudioRecorder({
    onRecordingComplete: handleRecordingComplete,
  })

  const startSession = async () => {
    if (!userId) return

    setIsLoading(true)
    try {
      const session = await onboardingApi.start(
        practiceId,
        userId,
        speakerName || undefined,
        speakerNotes || undefined
      )
      setSessionId(session.id)

      const phrasesData = await onboardingApi.getPhrases(session.id)
      setCategories(phrasesData)

      const total = phrasesData.reduce((sum: number, cat: Category) => sum + cat.total_phrases, 0)
      const completed = phrasesData.reduce((sum: number, cat: Category) => sum + cat.completed_phrases, 0)
      setProgress({ total, completed })
    } catch (err) {
      console.error('Failed to start session:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const downloadExport = () => {
    if (!sessionId) return
    const exportUrl = onboardingApi.exportSession(sessionId)
    window.open(exportUrl, '_blank')
  }

  const moveToNext = () => {
    if (!currentCategory) return

    // Find next unrecorded phrase in current category
    const nextInCategory = currentCategory.phrases.findIndex(
      (p, i) => i > currentPhraseIndex && !p.is_recorded
    )

    if (nextInCategory !== -1) {
      setCurrentPhraseIndex(nextInCategory)
      return
    }

    // Move to next category
    const nextCategoryIndex = categories.findIndex(
      (cat, i) => i > currentCategoryIndex && cat.completed_phrases < cat.total_phrases
    )

    if (nextCategoryIndex !== -1) {
      setCurrentCategoryIndex(nextCategoryIndex)
      const firstUnrecorded = categories[nextCategoryIndex].phrases.findIndex((p) => !p.is_recorded)
      setCurrentPhraseIndex(firstUnrecorded !== -1 ? firstUnrecorded : 0)
    }
  }

  const getCategoryName = (category: string): string => {
    const names: Record<string, string> = {
      tooth_designation: 'Zahnbezeichnungen',
      surface: 'Flächenbeschreibungen',
      diagnosis: 'Diagnosen',
      finding: 'Befunde',
      treatment: 'Behandlungsschritte',
      material: 'Materialien',
      instrument: 'Instrumente',
      anatomy: 'Anatomische Begriffe',
      sentence: 'Satzkombinationen',
    }
    return names[category] || category
  }

  const progressPercentage = progress.total > 0 ? (progress.completed / progress.total) * 100 : 0

  if (!sessionId) {
    return (
      <div className="py-8">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-4">Sprachtraining</h2>
          <p className="text-slate-600 mb-6 max-w-md mx-auto">
            Trainieren Sie das System mit Ihrer Stimme. Sprechen Sie ca. 200-250 zahnmedizinische
            Begriffe und Phrasen für optimale Erkennungsleistung.
          </p>
          <div className="text-sm text-slate-500 mb-4">
            <p>Geschätzte Dauer: 10-15 Minuten</p>
          </div>
        </div>

        {/* Speaker info form */}
        <div className="card mb-6">
          <h3 className="font-medium text-slate-800 mb-4">Sprecher-Informationen</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Name / Kennung *
              </label>
              <input
                type="text"
                value={speakerName}
                onChange={(e) => setSpeakerName(e.target.value)}
                placeholder="z.B. Dr. Müller, Assistenz Anna"
                className="w-full p-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-dental-500 focus:border-dental-500"
              />
              <p className="text-xs text-slate-500 mt-1">
                Wird für die Trainingsdaten verwendet
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Notizen (optional)
              </label>
              <textarea
                value={speakerNotes}
                onChange={(e) => setSpeakerNotes(e.target.value)}
                placeholder="z.B. Dialekt, Mikrofon-Setup, etc."
                rows={2}
                className="w-full p-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-dental-500 focus:border-dental-500"
              />
            </div>
          </div>
        </div>

        <button
          onClick={startSession}
          disabled={isLoading || !speakerName.trim()}
          className="btn btn-primary text-lg px-8 py-3 w-full"
        >
          {isLoading ? 'Wird gestartet...' : 'Training starten'}
        </button>

        {!speakerName.trim() && (
          <p className="text-sm text-slate-500 text-center mt-2">
            Bitte geben Sie einen Namen ein
          </p>
        )}
      </div>
    )
  }

  if (progress.completed >= progress.total) {
    return (
      <div className="text-center py-12">
        <div className="w-20 h-20 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-4">Training abgeschlossen!</h2>
        <p className="text-slate-600 mb-6">
          Vielen Dank{speakerName ? `, ${speakerName}` : ''}! Sie haben alle {progress.total} Phrasen aufgenommen.
        </p>

        {/* Export section */}
        <div className="card text-left mb-6">
          <h3 className="font-medium text-slate-800 mb-3">Trainingsdaten exportieren</h3>
          <p className="text-sm text-slate-600 mb-4">
            Laden Sie die Aufnahmen als ZIP-Datei herunter, um Whisper damit zu trainieren.
            Enthält alle Audio-Dateien und eine manifest.csv mit Metadaten.
          </p>
          <button
            onClick={downloadExport}
            className="btn btn-primary w-full flex items-center justify-center space-x-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Trainingsdaten herunterladen</span>
          </button>
        </div>

        <button
          onClick={() => {
            setSessionId(null)
            setCategories([])
            setProgress({ completed: 0, total: 0 })
            setSpeakerName('')
            setSpeakerNotes('')
          }}
          className="btn btn-secondary"
        >
          Neues Training starten
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div className="card">
        <div className="flex justify-between text-sm text-slate-600 mb-2">
          <span>Fortschritt</span>
          <span>{progress.completed} / {progress.total}</span>
        </div>
        <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-dental-500 transition-all duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <p className="text-sm text-slate-500 mt-2">
          {progressPercentage.toFixed(0)}% abgeschlossen
        </p>
      </div>

      {/* Category info */}
      {currentCategory && (
        <div className="card">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-medium text-dental-700">
              {getCategoryName(currentCategory.category)}
            </h3>
            <span className="text-sm text-slate-500">
              {currentCategory.completed_phrases} / {currentCategory.total_phrases}
            </span>
          </div>
          <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-dental-400 transition-all duration-300"
              style={{
                width: `${(currentCategory.completed_phrases / currentCategory.total_phrases) * 100}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Current phrase */}
      {currentPhrase && (
        <div className="card text-center py-8">
          <p className="text-sm text-slate-500 mb-2">Sprechen Sie:</p>
          <p className="text-2xl font-semibold text-slate-800 mb-6">
            "{currentPhrase.phrase_text}"
          </p>

          {/* Record button */}
          <div className="flex flex-col items-center">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`w-24 h-24 rounded-full transition-all duration-300 ${
                isRecording
                  ? 'bg-red-500 hover:bg-red-600 recording-pulse'
                  : 'bg-dental-600 hover:bg-dental-700'
              }`}
            >
              {isRecording ? (
                <div className="w-8 h-8 bg-white rounded mx-auto" />
              ) : (
                <svg className="w-12 h-12 text-white mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              )}
            </button>

            <p className="text-sm text-slate-500 mt-4">
              {isRecording
                ? `Aufnahme: ${duration.toFixed(1)}s`
                : 'Zum Aufnehmen tippen'}
            </p>
          </div>
        </div>
      )}

      {/* Skip button */}
      <button
        onClick={moveToNext}
        disabled={isRecording}
        className="btn btn-secondary w-full"
      >
        Überspringen
      </button>

      {/* Category selector */}
      <div className="card">
        <h4 className="text-sm font-medium text-slate-600 mb-3">Kategorien</h4>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat, index) => (
            <button
              key={cat.category}
              onClick={() => {
                setCurrentCategoryIndex(index)
                const firstUnrecorded = cat.phrases.findIndex((p) => !p.is_recorded)
                setCurrentPhraseIndex(firstUnrecorded !== -1 ? firstUnrecorded : 0)
              }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                index === currentCategoryIndex
                  ? 'bg-dental-600 text-white'
                  : cat.completed_phrases >= cat.total_phrases
                  ? 'bg-green-100 text-green-700'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {getCategoryName(cat.category)}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
