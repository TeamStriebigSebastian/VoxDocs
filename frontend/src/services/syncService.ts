/**
 * Sync Service - Handles background synchronization of offline recordings
 */

import { audioApi, onboardingApi } from './api'
import { offlineStorage } from './offlineStorage'
import { db, SyncQueueItem } from '../db'

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
    // Check every 30 seconds for pending uploads to ensure nothing stuck
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

  // Main Sync Entrypoint
  async sync(): Promise<void> {
    if (!this.isOnline || this.isSyncing) return

    this.isSyncing = true
    await this.notifyListeners('syncing')

    try {
      // Sync legacy recordings
      await this.syncRecordings()

      // Sync phrase recordings
      await this.syncPhrases()

      // Sync Generic Platform Data (Queue)
      await this.processSyncQueue()

      await this.notifyListeners('idle')
    } catch (error) {
      console.error('Sync error:', error)
      await this.notifyListeners('error')
    } finally {
      this.isSyncing = false
    }
  }

  // --- Auth Helper ---
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // --- Generic Platform Sync ---
  private async processSyncQueue() {
    const queueItems = await db.syncQueue.orderBy('created_at').toArray();

    for (const item of queueItems) {
      try {
        if (item.type === 'entry' && item.action === 'create') {
          await this.syncEntry(item);
        } else if (item.type === 'task') {
          await this.syncTask(item);
        }
        // Remove from queue on success
        if (item.id) await db.syncQueue.delete(item.id);
      } catch (error) {
        console.error('Failed to process sync item:', item, error);
      }
    }
  }

  private async syncEntry(item: SyncQueueItem) {
    const localEntry = item.payload as any; // Cast to LocalEntry
    const formData = new FormData();
    formData.append('case_uuid', localEntry.case_uuid);
    formData.append('text', localEntry.text || '');
    if (localEntry.category_id) formData.append('category_id', String(localEntry.category_id));
    if (localEntry.parent_entry_id) formData.append('parent_entry_id', String(localEntry.parent_entry_id));

    // Handle blobs
    if (localEntry.pendingAudioBlob) {
      formData.append('audio_file', localEntry.pendingAudioBlob, 'audio.wav');
    }

    const res = await fetch('/api/entries/', {
      method: 'POST',
      headers: this.getAuthHeaders(), // No Content-Type for FormData
      body: formData
    });

    if (!res.ok) throw new Error('Failed to sync entry');

    // Update local entry with server data (mark synced)
    const existing = await db.entries.where('uuid').equals(localEntry.uuid).first();
    if (existing && existing.id) {
      await db.entries.update(existing.id, {
        ...existing,
        synced: true,
        pendingAudioBlob: undefined,
        pendingImageBlob: undefined
      });
    }
  }

  private async syncTask(item: SyncQueueItem) {
    const localTask = item.payload as any;

    if (item.action === 'create') {
      const res = await fetch('/api/tasks/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders()
        },
        body: JSON.stringify({
          case_uuid: localTask.case_uuid,
          title: localTask.title,
          task_type: localTask.task_type || 'one_shot'
        })
      });

      if (!res.ok) throw new Error('Failed to sync task');

      const serverTask = await res.json();

      // Update local task
      const existing = await db.tasks.where('case_uuid').equals(localTask.case_uuid).filter(t => t.title === localTask.title).first();
      if (existing && existing.id) {
        await db.tasks.update(existing.id, {
          server_id: serverTask.id,
          synced: true
        });
      }
    }
  }

  // --- Legacy Sync Methods ---

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
          recording.processImmediately,
          recording.recordedAt
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
    processImmediately = false,
    recordedAt?: Date
  ): Promise<{ success: boolean; offline: boolean; result?: unknown }> {
    // Use provided recordedAt or current time as fallback
    const actualRecordedAt = recordedAt || new Date()

    if (this.isOnline) {
      try {
        const result = await audioApi.upload(blob, practiceId, roomId, processImmediately, actualRecordedAt)
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
      processImmediately,
      recordedAt: actualRecordedAt
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
