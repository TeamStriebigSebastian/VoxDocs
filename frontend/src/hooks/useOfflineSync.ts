import { useState, useEffect } from 'react'
import { syncService } from '../services/syncService'
import { offlineStorage } from '../services/offlineStorage'

interface SyncState {
  isOnline: boolean
  isSyncing: boolean
  pendingRecordings: number
  pendingPhrases: number
}

export function useOfflineSync() {
  const [state, setState] = useState<SyncState>({
    isOnline: navigator.onLine,
    isSyncing: false,
    pendingRecordings: 0,
    pendingPhrases: 0
  })

  useEffect(() => {
    // Get initial pending count
    const loadPendingCount = async () => {
      const pending = await offlineStorage.getPendingCount()
      setState(prev => ({
        ...prev,
        pendingRecordings: pending.recordings,
        pendingPhrases: pending.phrases
      }))
    }

    loadPendingCount()

    // Subscribe to sync status changes
    const unsubscribe = syncService.subscribe((status, pending) => {
      setState(prev => ({
        ...prev,
        isSyncing: status === 'syncing',
        pendingRecordings: pending.recordings,
        pendingPhrases: pending.phrases
      }))
    })

    // Listen for online/offline
    const handleOnline = () => setState(prev => ({ ...prev, isOnline: true }))
    const handleOffline = () => setState(prev => ({ ...prev, isOnline: false }))

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      unsubscribe()
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const triggerSync = () => {
    syncService.sync()
  }

  const totalPending = state.pendingRecordings + state.pendingPhrases

  return {
    ...state,
    totalPending,
    triggerSync
  }
}
