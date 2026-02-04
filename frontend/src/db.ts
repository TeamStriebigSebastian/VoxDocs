import Dexie, { Table } from 'dexie'

// --- Interfaces ---

export interface LocalCase {
    id?: number
    uuid: string
    title: string
    status: string
    group_id: number
    synced: boolean
    lastModified: number
}

export interface LocalEntry {
    id?: number
    uuid: string
    case_uuid: string
    text: string
    created_at: string
    has_audio: boolean
    has_image?: boolean
    category_id: number | null
    author_id: number
    author_name?: string
    synced: boolean
    parent_entry_id?: number | null
    parent_entry_uuid?: string | null  // UUID for sync purposes
    pendingAudioBlob?: Blob
    pendingImageBlob?: Blob
    translations?: { language_code: string, translated_text: string }[]
    structured_data?: any
}

export interface LocalTask {
    id?: number
    server_id?: number
    case_uuid: string
    title: string
    status: 'active' | 'completed'
    task_type: string
    synced: boolean
    translations?: { language_code: string, title: string }[]
}

export interface SyncQueueItem {
    id?: number
    type: 'entry' | 'task' | 'case'
    action: 'create' | 'update' | 'delete'
    payload: unknown
    created_at: number
    retries: number
}

// --- Database Class ---

class VoxDocsDB extends Dexie {
    cases!: Table<LocalCase>
    entries!: Table<LocalEntry>
    tasks!: Table<LocalTask>
    syncQueue!: Table<SyncQueueItem>

    constructor() {
        super('VoxDocsDB')

        this.version(1).stores({
            cases: '++id, uuid, group_id, synced',
            entries: '++id, uuid, case_uuid, synced, created_at',
            tasks: '++id, server_id, case_uuid, synced',
            syncQueue: '++id, type, created_at'
        })

        // Version 2: Add compound index for efficient querying by case + date
        this.version(2).stores({
            entries: '++id, uuid, case_uuid, synced, created_at, [case_uuid+created_at]'
        })
    }
}

export const db = new VoxDocsDB()

// --- Helper Functions ---

/**
 * Generate a UUID for local entries before sync
 */
export function generateLocalUUID(): string {
    return crypto.randomUUID()
}
