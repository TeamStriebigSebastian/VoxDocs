/**
 * Offline Storage Service using IndexedDB
 * Stores recordings locally when offline and syncs when back online
 */

const DB_NAME = 'voxdocs-offline'
const DB_VERSION = 1
const RECORDINGS_STORE = 'pending-recordings'
const PHRASE_STORE = 'pending-phrases'

interface PendingRecording {
  id: string
  blob: Blob
  practiceId: number
  roomId?: number
  processImmediately: boolean
  recordedAt: Date  // When the recording was actually made
  createdAt: Date   // When it was saved to offline storage
  retryCount: number
  lastError?: string
}

interface PendingPhrase {
  id: string
  sessionId: number
  blob: Blob
  category: string
  phraseIndex: number
  phraseText: string
  createdAt: Date
  retryCount: number
  lastError?: string
}

class OfflineStorageService {
  private db: IDBDatabase | null = null
  private dbPromise: Promise<IDBDatabase> | null = null

  async init(): Promise<IDBDatabase> {
    if (this.db) return this.db

    if (this.dbPromise) return this.dbPromise

    this.dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        resolve(this.db)
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // Create recordings store
        if (!db.objectStoreNames.contains(RECORDINGS_STORE)) {
          const recordingsStore = db.createObjectStore(RECORDINGS_STORE, { keyPath: 'id' })
          recordingsStore.createIndex('createdAt', 'createdAt', { unique: false })
        }

        // Create phrase recordings store
        if (!db.objectStoreNames.contains(PHRASE_STORE)) {
          const phraseStore = db.createObjectStore(PHRASE_STORE, { keyPath: 'id' })
          phraseStore.createIndex('sessionId', 'sessionId', { unique: false })
          phraseStore.createIndex('createdAt', 'createdAt', { unique: false })
        }
      }
    })

    return this.dbPromise
  }

  // Recording methods
  async savePendingRecording(recording: Omit<PendingRecording, 'id' | 'createdAt' | 'retryCount'>): Promise<string> {
    const db = await this.init()
    const id = `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([RECORDINGS_STORE], 'readwrite')
      const store = transaction.objectStore(RECORDINGS_STORE)

      const pendingRecording: PendingRecording = {
        ...recording,
        id,
        createdAt: new Date(),
        retryCount: 0
      }

      const request = store.add(pendingRecording)

      request.onsuccess = () => resolve(id)
      request.onerror = () => reject(request.error)
    })
  }

  async getPendingRecordings(): Promise<PendingRecording[]> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([RECORDINGS_STORE], 'readonly')
      const store = transaction.objectStore(RECORDINGS_STORE)
      const request = store.getAll()

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  async deletePendingRecording(id: string): Promise<void> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([RECORDINGS_STORE], 'readwrite')
      const store = transaction.objectStore(RECORDINGS_STORE)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async updateRecordingRetry(id: string, error: string): Promise<void> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([RECORDINGS_STORE], 'readwrite')
      const store = transaction.objectStore(RECORDINGS_STORE)
      const getRequest = store.get(id)

      getRequest.onsuccess = () => {
        const recording = getRequest.result as PendingRecording
        if (recording) {
          recording.retryCount += 1
          recording.lastError = error
          store.put(recording)
        }
        resolve()
      }
      getRequest.onerror = () => reject(getRequest.error)
    })
  }

  // Phrase recording methods
  async savePendingPhrase(phrase: Omit<PendingPhrase, 'id' | 'createdAt' | 'retryCount'>): Promise<string> {
    const db = await this.init()
    const id = `phrase_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([PHRASE_STORE], 'readwrite')
      const store = transaction.objectStore(PHRASE_STORE)

      const pendingPhrase: PendingPhrase = {
        ...phrase,
        id,
        createdAt: new Date(),
        retryCount: 0
      }

      const request = store.add(pendingPhrase)

      request.onsuccess = () => resolve(id)
      request.onerror = () => reject(request.error)
    })
  }

  async getPendingPhrases(sessionId?: number): Promise<PendingPhrase[]> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([PHRASE_STORE], 'readonly')
      const store = transaction.objectStore(PHRASE_STORE)

      if (sessionId) {
        const index = store.index('sessionId')
        const request = index.getAll(sessionId)
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      } else {
        const request = store.getAll()
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      }
    })
  }

  async deletePendingPhrase(id: string): Promise<void> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([PHRASE_STORE], 'readwrite')
      const store = transaction.objectStore(PHRASE_STORE)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  async updatePhraseRetry(id: string, error: string): Promise<void> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([PHRASE_STORE], 'readwrite')
      const store = transaction.objectStore(PHRASE_STORE)
      const getRequest = store.get(id)

      getRequest.onsuccess = () => {
        const phrase = getRequest.result as PendingPhrase
        if (phrase) {
          phrase.retryCount += 1
          phrase.lastError = error
          store.put(phrase)
        }
        resolve()
      }
      getRequest.onerror = () => reject(getRequest.error)
    })
  }

  // Utility methods
  async getPendingCount(): Promise<{ recordings: number; phrases: number }> {
    const recordings = await this.getPendingRecordings()
    const phrases = await this.getPendingPhrases()
    return {
      recordings: recordings.length,
      phrases: phrases.length
    }
  }

  async clearAll(): Promise<void> {
    const db = await this.init()

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([RECORDINGS_STORE, PHRASE_STORE], 'readwrite')

      transaction.objectStore(RECORDINGS_STORE).clear()
      transaction.objectStore(PHRASE_STORE).clear()

      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error)
    })
  }
}

export const offlineStorage = new OfflineStorageService()

// Export types
export type { PendingRecording, PendingPhrase }
