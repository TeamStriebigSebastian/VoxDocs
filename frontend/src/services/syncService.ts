/**
 * Sync Service - Handles background synchronization of offline recordings
 */

import { audioApi, onboardingApi } from './api'
import { offlineStorage } from './offlineStorage'

type SyncStatus = 'idle' | 'syncing' | 'error'
type SyncListener = (status: SyncStatus, pending: { recordings: number; phrases: number }) => void

class SyncService {
  private isOnline = navigator.onLine
  private isSyncing = false
  private listeners: Set<SyncListener> = new Set()
  private syncInterval: number | null = null

  constructor() {
    // Listen for online/offline events
    window.addEventListener('online', () => this.handleOnline())
    window.addEventListener('offline', () => this.handleOffline())

    // Initialize
    this.init()
  }

  private async init() {
    await offlineStorage.init()

    // Start periodic sync check
    this.startPeriodicSync()

    // Sync on startup if online
    if (this.isOnline) {
      this.sync()
    }
  }

  private handleOnline() {
    this.isOnline = true
    console.log('Network online - starting sync')
    this.sync()
  }

  private handleOffline() {
    this.isOnline = false
    console.log('Network offline - uploads will be queued')
  }

  private startPeriodicSync() {
    // Check every 30 seconds for pending uploads
    this.syncInterval = window.setInterval(() => {
      if (this.isOnline && !this.isSyncing) {
        this.sync()
      }
    }, 30000)
  }

  // Subscribe to sync status updates
  subscribe(listener: SyncListener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private async notifyListeners(status: SyncStatus) {
    const pending = await offlineStorage.getPendingCount()
    this.listeners.forEach(listener => listener(status, pending))
  }

  async sync(): Promise<void> {
    if (!this.isOnline || this.isSyncing) return

    this.isSyncing = true
    await this.notifyListeners('syncing')

    try {
      // Sync recordings
      await this.syncRecordings()

      // Sync phrase recordings
      await this.syncPhrases()

      await this.notifyListeners('idle')
    } catch (error) {
      console.error('Sync error:', error)
      await this.notifyListeners('error')
    } finally {
      this.isSyncing = false
    }
  }

  private async syncRecordings(): Promise<void> {
    const pendingRecordings = await offlineStorage.getPendingRecordings()

    for (const recording of pendingRecordings) {
      if (recording.retryCount >= 5) {
        console.warn(`Recording ${recording.id} exceeded max retries, skipping`)
        continue
      }

      try {
        await audioApi.upload(
          recording.blob,
          recording.practiceId,
          recording.roomId,
          recording.processImmediately
        )

        await offlineStorage.deletePendingRecording(recording.id)
        console.log(`Successfully synced recording ${recording.id}`)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error'
        await offlineStorage.updateRecordingRetry(recording.id, errorMessage)
        console.error(`Failed to sync recording ${recording.id}:`, error)
      }
    }
  }

  private async syncPhrases(): Promise<void> {
    const pendingPhrases = await offlineStorage.getPendingPhrases()

    for (const phrase of pendingPhrases) {
      if (phrase.retryCount >= 5) {
        console.warn(`Phrase ${phrase.id} exceeded max retries, skipping`)
        continue
      }

      try {
        await onboardingApi.recordPhrase(
          phrase.sessionId,
          phrase.blob,
          phrase.category,
          phrase.phraseIndex,
          phrase.phraseText
        )

        await offlineStorage.deletePendingPhrase(phrase.id)
        console.log(`Successfully synced phrase ${phrase.id}`)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error'
        await offlineStorage.updatePhraseRetry(phrase.id, errorMessage)
        console.error(`Failed to sync phrase ${phrase.id}:`, error)
      }
    }
  }

  // Public API for uploading with offline fallback
  async uploadRecording(
    blob: Blob,
    practiceId: number,
    roomId?: number,
    processImmediately = false
  ): Promise<{ success: boolean; offline: boolean; result?: unknown }> {
    if (this.isOnline) {
      try {
        const result = await audioApi.upload(blob, practiceId, roomId, processImmediately)
        return { success: true, offline: false, result }
      } catch (error) {
        console.error('Upload failed, saving offline:', error)
        // Fall through to offline storage
      }
    }

    // Save offline
    const id = await offlineStorage.savePendingRecording({
      blob,
      practiceId,
      roomId,
      processImmediately
    })

    await this.notifyListeners('idle')

    return { success: true, offline: true, result: { offlineId: id } }
  }

  async uploadPhrase(
    sessionId: number,
    blob: Blob,
    category: string,
    phraseIndex: number,
    phraseText: string
  ): Promise<{ success: boolean; offline: boolean; result?: unknown }> {
    if (this.isOnline) {
      try {
        const result = await onboardingApi.recordPhrase(
          sessionId,
          blob,
          category,
          phraseIndex,
          phraseText
        )
        return { success: true, offline: false, result }
      } catch (error) {
        console.error('Phrase upload failed, saving offline:', error)
        // Fall through to offline storage
      }
    }

    // Save offline
    const id = await offlineStorage.savePendingPhrase({
      sessionId,
      blob,
      category,
      phraseIndex,
      phraseText
    })

    await this.notifyListeners('idle')

    return { success: true, offline: true, result: { offlineId: id } }
  }

  // Get current status
  getStatus(): { online: boolean; syncing: boolean } {
    return {
      online: this.isOnline,
      syncing: this.isSyncing
    }
  }

  // Cleanup
  destroy() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
    }
  }
}

export const syncService = new SyncService()
