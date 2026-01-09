import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { onboardingApi } from '../services/api'
import { useAudioRecorder } from '../hooks/useAudioRecorder'

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

  const currentCategory = categories[currentCategoryIndex]
  const currentPhrase = currentCategory?.phrases[currentPhraseIndex]

  const handleRecordingComplete = async (blob: Blob) => {
    if (!sessionId || !currentCategory || !currentPhrase) return

    try {
      await onboardingApi.recordPhrase(
        sessionId,
        blob,
        currentCategory.category,
        currentPhrase.phrase_index,
        currentPhrase.phrase_text
      )

      // Update local state
      const updatedCategories = [...categories]
      updatedCategories[currentCategoryIndex].phrases[currentPhraseIndex].is_recorded = true
      updatedCategories[currentCategoryIndex].completed_phrases += 1
      setCategories(updatedCategories)

      setProgress((prev) => ({ ...prev, completed: prev.completed + 1 }))

      // Move to next phrase
      moveToNext()
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
      const session = await onboardingApi.start(practiceId, userId)
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
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-slate-800 mb-4">Sprachtraining</h2>
        <p className="text-slate-600 mb-6 max-w-md mx-auto">
          Trainieren Sie das System mit Ihrer Stimme. Sprechen Sie ca. 200-250 zahnmedizinische
          Begriffe und Phrasen für optimale Erkennungsleistung.
        </p>
        <div className="text-sm text-slate-500 mb-8">
          <p>Geschätzte Dauer: 10-15 Minuten</p>
        </div>
        <button
          onClick={startSession}
          disabled={isLoading}
          className="btn btn-primary text-lg px-8 py-3"
        >
          {isLoading ? 'Wird gestartet...' : 'Training starten'}
        </button>
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
          Vielen Dank! Sie haben alle {progress.total} Phrasen aufgenommen.
          Das System wird mit Ihren Aufnahmen trainiert.
        </p>
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
