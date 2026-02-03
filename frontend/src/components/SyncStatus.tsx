import { useOfflineSync } from '../hooks/useOfflineSync'

export default function SyncStatus() {
  const { isOnline, isSyncing, totalPending, triggerSync } = useOfflineSync()

  // Don't show if online and no pending items
  if (isOnline && totalPending === 0 && !isSyncing) {
    return null
  }

  return (
    <div className="fixed top-16 left-4 right-4 max-w-lg mx-auto z-40">
      <div
        className={`rounded-lg shadow-lg p-3 flex items-center justify-between ${
          isOnline ? 'bg-blue-50 border border-blue-200' : 'bg-yellow-50 border border-yellow-200'
        }`}
      >
        <div className="flex items-center space-x-3">
          {/* Status indicator */}
          <div className="relative">
            {isSyncing ? (
              <svg className="w-5 h-5 text-blue-600 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : isOnline ? (
              <CloudIcon className="w-5 h-5 text-blue-600" />
            ) : (
              <OfflineIcon className="w-5 h-5 text-yellow-600" />
            )}
          </div>

          {/* Status text */}
          <div>
            <p className={`text-sm font-medium ${isOnline ? 'text-blue-800' : 'text-yellow-800'}`}>
              {isSyncing
                ? 'Wird synchronisiert...'
                : isOnline
                ? `${totalPending} Aufnahme${totalPending !== 1 ? 'n' : ''} ausstehend`
                : 'Offline-Modus'}
            </p>
            {!isOnline && (
              <p className="text-xs text-yellow-600">
                Aufnahmen werden gespeichert und später hochgeladen
              </p>
            )}
          </div>
        </div>

        {/* Sync button (only when online with pending) */}
        {isOnline && totalPending > 0 && !isSyncing && (
          <button
            onClick={triggerSync}
            className="text-blue-600 hover:text-blue-800 p-2"
            aria-label="Jetzt synchronisieren"
          >
            <SyncIcon className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  )
}

function CloudIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  )
}

function OfflineIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
    </svg>
  )
}

function SyncIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  )
}
