import { useState } from 'react'
import { usePWAInstall } from '../hooks/usePWAInstall'

export default function InstallButton() {
  const { isInstallable, isInstalled, install } = usePWAInstall()
  const [showBanner, setShowBanner] = useState(true)

  if (isInstalled || !isInstallable || !showBanner) {
    return null
  }

  const handleInstall = async () => {
    const accepted = await install()
    if (!accepted) {
      // User dismissed, hide the banner
      setShowBanner(false)
    }
  }

  return (
    <div className="fixed bottom-20 left-4 right-4 max-w-lg mx-auto z-50">
      <div className="bg-dental-600 text-white rounded-lg shadow-lg p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-white/20 rounded-lg p-2">
            <DownloadIcon className="w-6 h-6" />
          </div>
          <div>
            <p className="font-medium">App installieren</p>
            <p className="text-sm text-dental-100">Schnellerer Zugriff & Offline-Nutzung</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowBanner(false)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Schließen"
          >
            <CloseIcon className="w-5 h-5" />
          </button>
          <button
            onClick={handleInstall}
            className="bg-white text-dental-600 px-4 py-2 rounded-lg font-medium hover:bg-dental-50 transition-colors"
          >
            Installieren
          </button>
        </div>
      </div>
    </div>
  )
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  )
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}
