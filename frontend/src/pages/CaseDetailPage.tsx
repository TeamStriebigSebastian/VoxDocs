import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, FileText, Mic, CheckCircle2, Circle, Plus, Trash2, Camera, Image as ImageIcon, LayoutGrid, ChevronDown, Globe } from 'lucide-react'
import Dexie from 'dexie'
import { useLiveQuery } from 'dexie-react-hooks'
import SmartVoiceButton from '../components/SmartVoiceButton'
import { useWebSocketNotifications } from '../hooks/useWebSocketNotifications'
import { db, LocalEntry, LocalTask, generateLocalUUID } from '../db'
import { syncService } from '../services/syncService'
import { useAuth } from '../contexts/AuthContext'
import { authService, User } from '../services/authService'
import { ImageAnnotationModal } from '../components/ImageAnnotationModal'

interface Category {
    id: number
    name: string
}

// Type alias for local entries displayed in the timeline
type Entry = LocalEntry

// Secure Image Component to fetch protected images
const SecureImage = ({ entryUuid, className, pendingBlob }: { entryUuid: string, className?: string, pendingBlob?: Blob }) => {
    const { accessToken } = useAuth()
    const [src, setSrc] = useState<string | null>(null)

    useEffect(() => {
        if (pendingBlob) {
            setSrc(URL.createObjectURL(pendingBlob))
            return
        }

        let active = true
        if (accessToken) {
            fetch(`/api/entries/${entryUuid}/image`, {
                headers: { Authorization: `Bearer ${accessToken}` }
            })
                .then(res => {
                    if (res.ok) return res.blob()
                    throw new Error('Failed to load image')
                })
                .then(blob => {
                    if (active) setSrc(URL.createObjectURL(blob))
                })
                .catch(() => { /* ignore */ })
        }
        return () => { active = false }
    }, [entryUuid, accessToken, pendingBlob])

    if (!src) return (
        <div className={`flex items-center justify-center text-slate-300 bg-slate-100 ${className}`}>
            <ImageIcon className="w-8 h-8 opacity-50" />
        </div>
    )

    return <img src={src} className={`${className} object-cover`} alt="" />
}

export default function CaseDetailPage() {
    const { uuid } = useParams()
    const navigate = useNavigate()

    // Pagination State
    const [visibleCount, setVisibleCount] = useState(20)

    // Reactive queries from local database
    const caseFile = useLiveQuery(
        () => uuid ? db.cases.where('uuid').equals(uuid).first() : undefined,
        [uuid]
    )

    // Optimized Query using Compound Index [case_uuid+created_at]
    const entries = useLiveQuery(
        () => {
            if (!uuid) return []
            // Use compound index to get [case_uuid, created_at]
            // We want specific case, sorted by created_at DESC
            // Range: [uuid, MinDate] to [uuid, MaxDate]
            // Reverse = MaxDate to MinDate (Newest first)
            return db.entries
                .where('[case_uuid+created_at]')
                .between([uuid, Dexie.minKey], [uuid, Dexie.maxKey])
                .reverse()
                .limit(visibleCount)
                .toArray()
        },
        [uuid, visibleCount],
        []
    )

    const tasks = useLiveQuery(
        () => uuid ? db.tasks.where('case_uuid').equals(uuid).toArray() : [],
        [uuid],
        []
    )

    // Categories still fetched from network (group-specific, rarely changes)
    const [categories, setCategories] = useState<Category[]>([])
    const [loading, setLoading] = useState(true)

    const { accessToken, logout, user } = useAuth()
    const [currentUser, setCurrentUser] = useState<User | null>(null)
    const [serverDefaultLang, setServerDefaultLang] = useState<string>('de')

    useEffect(() => {
        const token = localStorage.getItem('token')
        if (token) {
            Promise.all([
                authService.getMe(),
                fetch('/api/settings/', { headers: { 'Authorization': `Bearer ${token}` } }).then(r => r.json())
            ]).then(([userData, settings]) => {
                setCurrentUser(userData)
                if (settings.default_language) {
                    setServerDefaultLang(settings.default_language)
                }
            }).catch(console.error)
        }
    }, [])

    const [newEntryText, setNewEntryText] = useState('')

    const handleUpdateStatus = async (newStatus: string) => {
        if (!caseFile || !accessToken) return
        if (!confirm(`Status wirklich auf "${newStatus}" ändern?`)) return

        try {
            const res = await fetch(`/api/cases/${caseFile.uuid}`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            })

            if (res.ok) {
                const data = await res.json()
                // Update local DB
                if (caseFile.id) {
                    await db.cases.update(caseFile.id, { status: data.status, synced: true })
                }
            } else {
                alert("Fehler beim Aktualisieren des Status (Berechtigung fehlt?)")
            }
        } catch (e) {
            console.error(e)
        }
    }
    const [audioFile, setAudioFile] = useState<File | null>(null)
    const [imageFile, setImageFile] = useState<File | null>(null)
    const [parentEntryId, setParentEntryId] = useState<number | null>(null)

    // Annotation / Attachment State
    const [annotationFile, setAnnotationFile] = useState<File | null>(null)
    const [isAnnotationOpen, setIsAnnotationOpen] = useState(false)
    const [attachmentParentId, setAttachmentParentId] = useState<number | null>(null)

    const [isSubmitting, setIsSubmitting] = useState(false)
    const [showTextInput, setShowTextInput] = useState(false)

    // Refs
    const fileInputRef = useRef<HTMLInputElement>(null)
    const attachmentInputRef = useRef<HTMLInputElement>(null)

    // Task Creation
    const [newTaskTitle, setNewTaskTitle] = useState('')
    const [showTaskInput, setShowTaskInput] = useState(false)

    // Start background sync - reuse existing syncService
    useEffect(() => {
        // The syncService is already initialized as a singleton
        // We just need to trigger sync on mount
        syncService.sync()
    }, [])

    // Real-time Updates (Server -> Local DB)
    useWebSocketNotifications((data) => {
        if (data.type === 'transcription_ready' && uuid) {
            console.log('Real-time update received, pulling data...')
            pullDataFromServer(uuid)
        }
    })

    // Initial data load
    useEffect(() => {
        if (uuid) {
            loadInitialData(uuid)
        }
    }, [uuid])

    // Pull data from server to local DB
    // Supports pagination for entries
    const pullDataFromServer = async (id: string, skip: number = 0, limit: number = 20) => {
        if (!navigator.onLine || !accessToken) return

        try {
            const headers = { 'Authorization': `Bearer ${accessToken}` }

            // Fetch case
            const caseRes = await fetch(`/api/cases/${id}`, { headers })
            if (caseRes.ok) {
                const caseData = await caseRes.json()
                const existing = await db.cases.where('uuid').equals(id).first()
                if (existing) {
                    await db.cases.update(existing.id!, { ...caseData, synced: true, lastModified: Date.now() })
                } else {
                    await db.cases.add({ ...caseData, synced: true, lastModified: Date.now() })
                }
            } else if (caseRes.status === 401) return logout()

            // Fetch entries (Paginated)
            const entriesRes = await fetch(`/api/entries/?case_uuid=${id}&limit=${limit}&skip=${skip}`, { headers })
            if (entriesRes.ok) {
                const text = await entriesRes.text()
                try {
                    const cleanText = text.trim().replace(/^\uFEFF/, '')
                    const serverEntries = JSON.parse(cleanText)

                    if (Array.isArray(serverEntries)) {
                        for (const entry of serverEntries) {
                            // Strip server ID to avoid collision with local auto-inc ID
                            // We rely on UUID for uniqueness
                            const { id: serverId, ...entryData } = entry

                            const entryWithCaseUuid = { ...entryData, case_uuid: id, synced: true }
                            const existingEntry = await db.entries.where('uuid').equals(entry.uuid).first()

                            if (!existingEntry) {
                                await db.entries.add(entryWithCaseUuid)
                            } else if (existingEntry.synced) {
                                // Update synced entries with server data, preserving local ID
                                await db.entries.update(existingEntry.id!, entryWithCaseUuid)
                            }
                        }
                    } else {
                        console.error('[CaseDetailPage] Expected array for entries, got:', typeof serverEntries)
                    }
                } catch (e: any) {
                    console.error('[CaseDetailPage] JSON Parse Error (Entries):', e.message)
                }
            }

            // Fetch tasks
            const tasksRes = await fetch(`/api/tasks/?case_uuid=${id}`, { headers })
            if (tasksRes.ok) {
                const text = await tasksRes.text()
                try {
                    const cleanText = text.trim().replace(/^\uFEFF/, '')
                    const serverTasks = JSON.parse(cleanText)

                    if (Array.isArray(serverTasks)) {
                        for (const task of serverTasks) {
                            // Strip server ID to avoid collision
                            const { id: serverId, ...taskData } = task

                            const existingTask = await db.tasks.where('server_id').equals(serverId).first()

                            if (!existingTask) {
                                // Add new task
                                await db.tasks.add({ ...taskData, case_uuid: id, server_id: serverId, synced: true })
                            } else {
                                // Update existing task
                                await db.tasks.update(existingTask.id!, {
                                    status: task.status,
                                    title: task.title,
                                    case_uuid: id,
                                    synced: true
                                })
                            }
                        }
                    }
                } catch (e: any) {
                    console.error('[CaseDetailPage] JSON Parse Error (Tasks):', e.message)
                }
            }
        } catch (error) {
            console.error('[CaseDetailPage] Error pulling data:', error)
        }
    }

    const loadInitialData = async (id: string) => {
        try {
            setLoading(true)

            // Pull first page from server
            await pullDataFromServer(id, 0, 20)

            // Fetch categories (network-only for now)
            const localCase = await db.cases.where('uuid').equals(id).first()
            if (localCase && accessToken) {
                try {
                    const categoriesRes = await fetch(`/api/categories/?group_id=${localCase.group_id}`, {
                        headers: { 'Authorization': `Bearer ${accessToken}` }
                    })
                    if (categoriesRes.ok) setCategories(await categoriesRes.json())
                } catch {
                    // Offline, categories not available
                }
            }
        } catch (e) {
            console.error('[CaseDetailPage] Error loading data:', e)
        } finally {
            setLoading(false)
        }
    }

    // Offline-First Entry Creation
    const handleSubmitEntry = async (e: React.FormEvent) => {
        e.preventDefault()
        if ((!newEntryText.trim() && !audioFile && !imageFile) || !caseFile) return

        try {
            setIsSubmitting(true)

            // Create local entry immediately (optimistic update)
            const localEntry: LocalEntry = {
                uuid: generateLocalUUID(),
                case_uuid: caseFile.uuid,
                text: newEntryText,
                created_at: new Date().toISOString(),
                has_audio: !!audioFile,
                has_image: !!imageFile,
                category_id: null,
                author_id: 0, // Will be updated by server
                synced: false,
                parent_entry_id: parentEntryId,
                pendingAudioBlob: audioFile ? await audioFile.arrayBuffer().then(b => new Blob([b])) : undefined,
                pendingImageBlob: imageFile ? await imageFile.arrayBuffer().then(b => new Blob([b])) : undefined,
            }

            await db.entries.add(localEntry)

            // Clear form immediately (optimistic)
            setNewEntryText('')
            setAudioFile(null)
            setImageFile(null)
            setParentEntryId(null)
            setShowTextInput(false)

            // Add to sync queue and try to sync
            await db.syncQueue.add({
                type: 'entry',
                action: 'create',
                payload: localEntry,
                created_at: Date.now(),
                retries: 0,
            })

            // Trigger background sync
            syncService.sync()

        } catch (error) {
            console.error('Error submitting entry:', error)
        } finally {
            setIsSubmitting(false)
        }
    }

    // Voice Handling with Offline Support
    const handleVoiceUpload = async (file: File, parentId?: number) => {
        if (!caseFile) return

        try {
            setIsSubmitting(true)

            // Convert File to Blob for storage
            const audioBlob = new Blob([await file.arrayBuffer()], { type: file.type })

            // Create local entry immediately
            const localEntry: LocalEntry = {
                uuid: generateLocalUUID(),
                case_uuid: caseFile.uuid,
                text: '',
                created_at: new Date().toISOString(),
                has_audio: true,
                category_id: null,
                author_id: 0,
                synced: false,
                pendingAudioBlob: audioBlob,
                parent_entry_id: parentId || undefined,
                structured_data: parentId ? { is_attachment: true } : {}
            }

            await db.entries.add(localEntry)

            // Add to sync queue
            await db.syncQueue.add({
                type: 'entry',
                action: 'create',
                payload: localEntry,
                created_at: Date.now(),
                retries: 0,
            })

            // Trigger sync
            syncService.sync()

        } catch (error) {
            console.error('Error uploading voice entry:', error)
        } finally {
            setIsSubmitting(false)
        }
    }

    // Attachment Handlers
    const handleAttachmentClick = (parentId: number) => {
        setAttachmentParentId(parentId)
        attachmentInputRef.current?.click()
    }

    const handleAttachmentSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setAnnotationFile(e.target.files[0])
            setIsAnnotationOpen(true)
            e.target.value = '' // reset
        }
    }

    const handleSaveAnnotation = async (blob: Blob) => {
        if (!attachmentParentId || !caseFile) return

        try {
            setIsSubmitting(true)
            // const file = new File([blob], "annotation.jpg", { type: "image/jpeg" }) // Unused

            const localEntry: LocalEntry = {
                uuid: generateLocalUUID(),
                case_uuid: caseFile.uuid,
                text: '',
                created_at: new Date().toISOString(),
                has_audio: false,
                has_image: true,
                category_id: null,
                author_id: 0,
                synced: false,
                pendingImageBlob: blob,
                parent_entry_id: attachmentParentId,
                structured_data: { is_attachment: true }
            }

            await db.entries.add(localEntry)

            await db.syncQueue.add({
                type: 'entry',
                action: 'create',
                payload: localEntry,
                created_at: Date.now(),
                retries: 0,
            })

            syncService.sync()

        } catch (e) {
            console.error(e)
        } finally {
            setIsSubmitting(false)
            setAttachmentParentId(null)
        }
    }

    // Task Creation with Offline Support
    const handleCreateTask = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newTaskTitle.trim() || !caseFile) return

        try {
            // Create local task immediately
            const localTask: LocalTask = {
                case_uuid: caseFile.uuid,
                title: newTaskTitle,
                status: 'active',
                task_type: 'one_shot',
                synced: false,
            }

            await db.tasks.add(localTask)

            setNewTaskTitle('')
            setShowTaskInput(false)

            // Add to sync queue
            await db.syncQueue.add({
                type: 'task',
                action: 'create',
                payload: localTask,
                created_at: Date.now(),
                retries: 0,
            })

            // Trigger sync
            syncService.sync()

        } catch (error) {
            console.error('Error creating task:', error)
        }
    }

    // Task Toggle with Optimistic Update
    const handleToggleTask = async (task: LocalTask) => {
        try {
            const newStatus = task.status === 'active' ? 'completed' : 'active'

            // Update local immediately
            await db.tasks.update(task.id!, { status: newStatus, synced: false })

            // Try to sync to server
            if (navigator.onLine && task.server_id && accessToken) {
                try {
                    await fetch(`/api/tasks/${task.server_id}/status`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${accessToken}`
                        },
                        body: JSON.stringify({ status: newStatus })
                    })
                    await db.tasks.update(task.id!, { synced: true })
                } catch {
                    // Will sync later
                }
            }
        } catch (error) {
            console.error('Error toggling task:', error)
        }
    }

    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setImageFile(e.target.files[0])
            setShowTextInput(true) // Auto-open text input for image context
        }
    }

    if (loading) return <div className="p-8 text-center">Lade Fall...</div>
    if (!caseFile) return <div className="p-8 text-center text-red-500">Fall nicht gefunden</div>

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">

            {/* LEFT: Task Sidebar (Desktop) / Top (Mobile) */}
            <aside className="w-full md:w-80 bg-white border-r border-slate-200 flex flex-col order-2 md:order-1 hidden md:flex">
                <div className="p-4 border-b border-slate-100 font-semibold text-slate-700 flex justify-between items-center">
                    <span>Plan / Aufgaben</span>
                    <button
                        onClick={() => setShowTaskInput(!showTaskInput)}
                        className="p-1 hover:bg-slate-100 rounded text-blue-600"
                    >
                        <Plus className="w-5 h-5" />
                    </button>
                </div>

                {showTaskInput && (
                    <form onSubmit={handleCreateTask} className="p-3 bg-slate-50 border-b border-slate-100">
                        <input
                            type="text"
                            value={newTaskTitle}
                            onChange={e => setNewTaskTitle(e.target.value)}
                            placeholder="Neue Aufgabe..."
                            className="w-full p-2 text-sm border border-slate-300 rounded mb-2"
                            autoFocus
                        />
                        <div className="flex justify-end space-x-2">
                            <button type="button" onClick={() => setShowTaskInput(false)} className="text-xs text-slate-500">Abbrechen</button>
                            <button type="submit" className="text-xs bg-blue-600 text-white px-2 py-1 rounded">Speichern</button>
                        </div>
                    </form>
                )}

                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {tasks.length === 0 && !showTaskInput && (
                        <div className="text-center py-8 text-slate-400 text-sm">Keine Aufgaben</div>
                    )}
                    {tasks.map((task: LocalTask) => (
                        <div
                            key={task.id}
                            onClick={() => handleToggleTask(task)}
                            className={`flex items-start p-2 rounded cursor-pointer group hover:bg-slate-50 ${task.status === 'completed' ? 'opacity-50' : ''}`}
                        >
                            <div className={`mt-0.5 mr-3 flex-shrink-0 ${task.status === 'completed' ? 'text-green-500' : 'text-slate-300 group-hover:text-slate-400'}`}>
                                {task.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
                            </div>
                            <div className="flex flex-col">
                                <span className={`text-sm ${task.status === 'completed' ? 'line-through text-slate-500' : 'text-slate-700'}`}>
                                    {task.title}
                                </span>
                                {(() => {
                                    const userLang = currentUser?.preferred_language || 'de'
                                    const serverLang = serverDefaultLang || 'de'
                                    const getTrans = (lang: string) => task.translations?.find(t => t.language_code === lang)?.title

                                    const userTrans = getTrans(userLang)
                                    const serverTrans = getTrans(serverLang)

                                    const displays = []
                                    if (userTrans) displays.push({ lang: userLang, text: userTrans })
                                    if (serverTrans && serverTrans !== userTrans && serverLang !== userLang) displays.push({ lang: serverLang, text: serverTrans })

                                    return displays.map((d, i) => (
                                        <span key={i} className="text-xs text-slate-400 italic mt-0.5 ml-1">
                                            [{d.lang.toUpperCase()}] {d.text}
                                        </span>
                                    ))
                                })()}
                            </div>
                        </div>
                    ))}
                </div>
            </aside>

            {/* RIGHT: Main Timeline */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden order-1 md:order-2">
                {/* Header */}
                <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm z-10">
                    <div className="flex items-center space-x-4">
                        <button
                            onClick={() => navigate('/platform/cases')}
                            className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-600"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                            <h1 className="text-xl font-bold text-slate-800">{caseFile.title}</h1>
                            <div className="flex items-center space-x-2 text-sm text-slate-500">
                                <span className={`px-2 rounded uppercase text-xs font-bold tracking-wider ${caseFile.status === 'active' ? 'bg-green-100 text-green-700' :
                                    caseFile.status === 'archived' ? 'bg-orange-100 text-orange-700' : 'bg-slate-200 text-slate-600'
                                    }`}>
                                    {caseFile.status}
                                </span>
                                <span>•</span>
                                <span>{entries.length} Einträge</span>
                            </div>
                        </div>
                    </div>

                    {/* Status Actions (Admin/Superuser) */}
                    {user?.roles.some(r => ['admin', 'superuser'].includes(r.role)) && (
                        <div className="flex items-center space-x-2">
                            {caseFile.status === 'active' && (
                                <button
                                    onClick={() => handleUpdateStatus('archived')}
                                    className="px-3 py-1 text-xs font-medium bg-orange-50 text-orange-700 rounded hover:bg-orange-100 border border-orange-200"
                                >
                                    Archivieren
                                </button>
                            )}
                            {caseFile.status !== 'active' && (
                                <button
                                    onClick={() => handleUpdateStatus('active')}
                                    className="px-3 py-1 text-xs font-medium bg-green-50 text-green-700 rounded hover:bg-green-100 border border-green-200"
                                >
                                    Reaktivieren
                                </button>
                            )}
                            {caseFile.status !== 'locked' && (
                                <button
                                    onClick={() => handleUpdateStatus('locked')}
                                    className="px-3 py-1 text-xs font-medium bg-slate-100 text-slate-700 rounded hover:bg-slate-200 border border-slate-300"
                                >
                                    Sperren
                                </button>
                            )}
                        </div>
                    )}
                </header>

                {/* Timeline */}
                <main className="flex-1 overflow-y-auto p-4 md:p-8 bg-slate-50 pb-40">
                    <div className="max-w-3xl mx-auto space-y-6">
                        {entries.length === 0 ? (
                            <div className="text-center py-12 text-slate-400">
                                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                <p>Noch keine Einträge vorhanden.</p>
                            </div>
                        ) : (
                            (() => {
                                // Grouping Logic: Tree Structure
                                const rootEntries = entries.filter(e => !e.parent_entry_id)

                                return rootEntries.map((entry: Entry) => {
                                    const category = categories.find((c: Category) => c.id === entry.category_id)
                                    const children = entries.filter(e => e.parent_entry_id === entry.id)

                                    // Separate attachments from replies (logic: attachments have is_attachment=true OR depends on implementation)
                                    // For now, let's treat media-only children and explicitly flagged ones as attachments
                                    // Make sure we check structured_data existence
                                    const attachments = children.filter(c => c.structured_data?.is_attachment || (c.has_image && !c.text) || (c.has_audio && !c.text))
                                    // Replies are the rest
                                    const replies = children.filter(c => !attachments.includes(c))

                                    return (
                                        <div key={entry.id} className="bg-white rounded-lg shadow-sm p-5 border border-slate-100 relative group">
                                            {/* Header */}
                                            <div className="flex justify-between items-start mb-3">
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs">
                                                        {entry.author_id}
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <span className="font-medium text-slate-700 leading-none">
                                                            User {entry.author_id}
                                                        </span>
                                                        <span className="text-xs text-slate-400 mt-0.5">{new Date(entry.created_at).toLocaleString('de-DE')}</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    {category && (
                                                        <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded border border-blue-200">
                                                            {category.name}
                                                        </span>
                                                    )}

                                                    {/* Action Buttons */}
                                                    <div className="flex space-x-1 opacity-10 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                if (entry.id) handleAttachmentClick(entry.id);
                                                            }}
                                                            className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-blue-600"
                                                            title="Foto anhängen"
                                                        >
                                                            <Camera className="w-4 h-4" />
                                                        </button>
                                                    </div>

                                                    <button
                                                        onClick={() => {
                                                            if (entry.id) {
                                                                setParentEntryId(entry.id);
                                                                setShowTextInput(true);
                                                            }
                                                        }}
                                                        className="text-xs text-slate-400 hover:text-blue-600 px-2 py-1 rounded bg-slate-50 border border-slate-100"
                                                    >
                                                        Antworten
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="pl-10">
                                                {/* Text Content */}
                                                {entry.text && (
                                                    <div className="mb-3 space-y-3">
                                                        {/* Primary/Original Text */}
                                                        <div className="text-slate-800 whitespace-pre-wrap leading-relaxed">
                                                            {(() => {
                                                                const snippet = entry.structured_data?.highlight_snippet
                                                                if (snippet && entry.text.includes(snippet)) {
                                                                    const parts = entry.text.split(snippet)
                                                                    return (
                                                                        <>
                                                                            {parts.map((part, i) => (
                                                                                <span key={i}>
                                                                                    {part}
                                                                                    {i < parts.length - 1 && (
                                                                                        <span className="bg-yellow-100 px-1 rounded mx-0.5">{snippet}</span>
                                                                                    )}
                                                                                </span>
                                                                            ))}
                                                                        </>
                                                                    )
                                                                }
                                                                return entry.text
                                                            })()}
                                                        </div>

                                                        {/* Translations Logic */}
                                                        {(() => {
                                                            const userLang = currentUser?.preferred_language || 'de'
                                                            const serverLang = serverDefaultLang || 'de'
                                                            const getTrans = (lang: string) => entry.translations?.find(t => t.language_code === lang)?.translated_text
                                                            const userTrans = getTrans(userLang)
                                                            const serverTrans = getTrans(serverLang)
                                                            const displays = []
                                                            if (userTrans) displays.push({ lang: userLang, text: userTrans })
                                                            if (serverTrans && serverTrans !== userTrans && serverLang !== userLang) displays.push({ lang: serverLang, text: serverTrans })

                                                            return displays.map((d, i) => (
                                                                <div key={i} className="pt-2 border-t border-slate-100/50">
                                                                    <div className="flex items-center space-x-2 mb-1">
                                                                        <Globe className="w-3 h-3 text-blue-400" />
                                                                        <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider">
                                                                            {d.lang.toUpperCase()}
                                                                        </span>
                                                                    </div>

                                                                    <p
                                                                        className="text-slate-600 text-[14px] leading-relaxed italic [&>mark]:bg-yellow-100 [&>mark]:px-1 [&>mark]:rounded [&>mark]:mx-0.5"
                                                                        dangerouslySetInnerHTML={{
                                                                            __html: d.text
                                                                                .replace(/</g, '&lt;').replace(/>/g, '&gt;')
                                                                                .replace(/&lt;mark&gt;/gi, '<mark>')
                                                                                .replace(/&lt;\/mark&gt;/gi, '</mark>')
                                                                        }}
                                                                    />
                                                                </div>
                                                            ))
                                                        })()}
                                                    </div>
                                                )}

                                                {/* Main Entry Media */}
                                                {entry.has_audio && (
                                                    <div className="inline-flex items-center space-x-3 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 mb-2">
                                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${entry.text ? 'bg-green-100' : 'bg-blue-100'}`}>
                                                            <Mic className={`w-4 h-4 ${entry.text ? 'text-green-600' : 'text-blue-600'}`} />
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium text-slate-700">Audio-Notiz</div>
                                                            <div className="text-xs text-slate-500">
                                                                {entry.text ? 'Transkription abgeschlossen' : 'Transkription ausstehend...'}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}

                                                {entry.has_image && (
                                                    <div className="inline-flex items-center space-x-3 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200">
                                                        <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                                            <ImageIcon className="w-4 h-4 text-green-600" />
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium text-slate-700">Foto aufgenommen</div>
                                                            <div className="text-xs text-slate-500">Bild gespeichert</div>
                                                        </div>
                                                        <div className="flex-1" />
                                                        {/* Main Entry Image Display using SecureImage */}
                                                        <div className="h-10 w-10 relative rounded overflow-hidden border border-slate-200">
                                                            <SecureImage
                                                                entryUuid={entry.uuid}
                                                                pendingBlob={entry.pendingImageBlob}
                                                                className="absolute inset-0 w-full h-full"
                                                            />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Visual Attachments Grid (Children) */}
                                                {attachments.length > 0 && (
                                                    <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
                                                        {attachments.map(att => (
                                                            <div key={att.id} className="relative aspect-square bg-slate-100 rounded-lg overflow-hidden border border-slate-200 group/att">
                                                                {att.has_image ? (
                                                                    <div className="w-full h-full flex items-center justify-center text-slate-400 bg-black/5">
                                                                        <SecureImage
                                                                            entryUuid={att.uuid}
                                                                            pendingBlob={att.pendingImageBlob}
                                                                            className="absolute inset-0 w-full h-full"
                                                                        />
                                                                    </div>
                                                                ) : att.has_audio ? (
                                                                    <div className="w-full h-full flex flex-col items-center justify-center bg-blue-50 text-blue-400">
                                                                        <Mic className="w-8 h-8" />
                                                                        <span className="text-xs mt-1">Audio</span>
                                                                    </div>
                                                                ) : null}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Text Replies (Threaded) */}
                                                {replies.length > 0 && (
                                                    <div className="mt-4 space-y-3 pl-4 border-l-2 border-slate-100">
                                                        {replies.map(reply => (
                                                            <div key={reply.id} className="bg-slate-50 p-3 rounded-lg text-sm text-slate-700 border border-slate-200">
                                                                <div className="flex items-center space-x-2 mb-1">
                                                                    <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-600">
                                                                        {reply.author_id}
                                                                    </div>
                                                                    <span className="font-semibold text-xs text-slate-600">User {reply.author_id}</span>
                                                                    <span className="text-[10px] text-slate-400">{new Date(reply.created_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}</span>
                                                                </div>
                                                                <div className="text-slate-800">{reply.text}</div>

                                                                {/* Audio reply indicator */}
                                                                {reply.has_audio && (
                                                                    <div className="mt-2 flex items-center space-x-2 text-blue-600 text-xs bg-blue-50 p-1.5 rounded w-fit">
                                                                        <Mic className="w-3 h-3" />
                                                                        <span>Audio-Notiz</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                            </div>
                                        </div>
                                    )
                                })
                            })()
                        )}
                    </div>
                    {/* Load More Button */}
                    <div className="flex justify-center mt-6 mb-8">
                        <button
                            onClick={async () => {
                                const newCount = visibleCount + 20
                                setVisibleCount(newCount)
                                // Fetch next batch from server IF online
                                if (caseFile) {
                                    // We fetch 'limit=20' but skip current visible (or specifically the next batch)
                                    // Actually, standard logic: we want records visibleCount to visibleCount+20
                                    // But simplifying: just fetch next 20
                                    await pullDataFromServer(caseFile.uuid, visibleCount, 20)
                                }
                            }}
                            className="flex items-center space-x-2 px-4 py-2 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-600 shadow-sm hover:bg-slate-50 transition-colors"
                        >
                            <ChevronDown className="w-4 h-4" />
                            <span>Ältere Einträge laden</span>
                        </button>
                    </div>
                </main>

                {/* Voice, Camera & Navigation Footer */}
                <footer className="fixed bottom-0 left-0 w-full bg-white border-t border-slate-200 p-4 z-50 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] safe-area-bottom">
                    <div className="max-w-3xl mx-auto">

                        {/* Hidden File Input for Camera */}
                        <input
                            type="file"
                            accept="image/*"
                            capture="environment"
                            ref={fileInputRef}
                            onChange={handleImageSelect}
                            className="hidden"
                        />
                        {/* Hidden Attachment Input */}
                        <input
                            type="file"
                            accept="image/*"
                            ref={attachmentInputRef}
                            onChange={handleAttachmentSelect}
                            className="hidden"
                        />

                        {/* Annotation Modal */}
                        <ImageAnnotationModal
                            isOpen={isAnnotationOpen}
                            imageFile={annotationFile}
                            onClose={() => setIsAnnotationOpen(false)}
                            onSave={handleSaveAnnotation}
                        />

                        {(imageFile || showTextInput) ? (
                            /* Alternate Mode: Typing or Image Review */
                            <form onSubmit={handleSubmitEntry} className="flex flex-col space-y-3 animate-in slide-in-from-bottom-5 fade-in duration-200">
                                {/* Image Review Card */}
                                {imageFile && (
                                    <div className="flex items-center justify-between bg-green-50 p-3 rounded-xl border border-green-100">
                                        <div className="flex items-center space-x-3 text-green-700">
                                            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                                                <ImageIcon className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <div className="text-sm font-bold">Foto aufgenommen</div>
                                                <div className="text-xs opacity-80">{imageFile.name}</div>
                                            </div>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setImageFile(null)
                                                // Close wrapper if no text
                                                if (!newEntryText) setShowTextInput(false)
                                            }}
                                            className="p-2 text-red-500 hover:bg-red-50 rounded-full"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    </div>
                                )}

                                {/* Reply Indicator */}
                                {parentEntryId && (
                                    <div className="flex items-center justify-between bg-blue-50 p-2 rounded-lg border border-blue-100 text-xs text-blue-700 mb-1">
                                        <span className="font-medium">Antwort / Korrektur zu Eintrag #{parentEntryId}</span>
                                        <button
                                            type="button"
                                            onClick={() => setParentEntryId(null)}
                                            className="p-1 hover:bg-blue-100 rounded-full"
                                        >
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                            </svg>
                                        </button>
                                    </div>
                                )}

                                {/* Text Input (Context for image) */}
                                <div className="flex gap-2 items-end">
                                    <textarea
                                        value={newEntryText}
                                        onChange={(e) => setNewEntryText(e.target.value)}
                                        className="flex-1 p-4 border border-slate-300 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none shadow-sm text-base"
                                        placeholder={imageFile ? "Notiz zum Foto..." : "Eintrag schreiben..."}
                                        rows={2}
                                        autoFocus
                                    />
                                    <button
                                        type="submit"
                                        disabled={(!newEntryText.trim() && !imageFile) || isSubmitting}
                                        className="bg-blue-600 text-white rounded-full p-4 flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg h-14 w-14 mb-1"
                                    >
                                        {isSubmitting ? (
                                            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        ) : (
                                            <Send className="w-6 h-6 ml-0.5" />
                                        )}
                                    </button>
                                </div>

                                <div className="flex justify-center">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setNewEntryText('')
                                            setImageFile(null)
                                            setShowTextInput(false)
                                        }}
                                        className="text-center text-xs text-slate-400 py-2 hover:text-slate-600"
                                    >
                                        Abbrechen
                                    </button>
                                </div>
                            </form>
                        ) : (
                            /* Default State: 3 Big Buttons (Grid, SmartMic, Camera) */
                            <div className="flex items-center justify-between px-4 pb-2">
                                {/* Left: Switch Case */}
                                <div className="flex flex-col items-center space-y-1">
                                    <button
                                        onClick={() => navigate('/platform/cases')}
                                        className="w-14 h-14 bg-slate-100 hover:bg-slate-200 rounded-2xl flex items-center justify-center shadow-sm transition-colors text-slate-600"
                                        title="Fall wechseln"
                                    >
                                        <LayoutGrid className="w-7 h-7 text-slate-600" />
                                    </button>
                                    <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Fälle</span>
                                </div>

                                {/* Center: Smart Mic Button */}
                                <div className="flex flex-col items-center -mt-6"> {/* Negative margin to pop up */}
                                    <SmartVoiceButton
                                        onRecordingComplete={handleVoiceUpload}
                                        isProcessing={isSubmitting}
                                    />
                                </div>

                                {/* Right: Camera Button */}
                                <div className="flex flex-col items-center space-y-1">
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        className="w-14 h-14 bg-slate-100 hover:bg-slate-200 rounded-2xl flex items-center justify-center shadow-sm transition-colors text-slate-600"
                                        title="Foto aufnehmen"
                                    >
                                        <Camera className="w-7 h-7" />
                                    </button>
                                    <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Foto</span>
                                </div>
                            </div>
                        )}
                    </div>
                </footer>
            </div >
        </div >
    )
}
