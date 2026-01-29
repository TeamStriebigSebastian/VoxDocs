import { useState, useEffect } from 'react'
import { Plus, Users, Shield, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface User {
    id: number
    username: string
    email: string | null
    is_active: boolean
    is_superuser: boolean
    roles: string[]
    preferred_language: string
}

export default function AdminPage() {
    const { accessToken } = useAuth()
    const [users, setUsers] = useState<User[]>([])
    const [showCreateModal, setShowCreateModal] = useState(false)

    // Form State
    const [newUsername, setNewUsername] = useState('')
    const [newEmail, setNewEmail] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [newRole, setNewRole] = useState('user')
    const [newLanguage, setNewLanguage] = useState('de')

    useEffect(() => {
        if (accessToken) fetchUsers()
    }, [accessToken])

    const fetchUsers = async () => {
        try {
            const res = await fetch('/api/users/', {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            })
            if (res.ok) setUsers(await res.json())
        } catch (error) {
            console.error('Failed to fetch users', error)
        } finally {
            // Loading handled implicitly or globally
        }
    }

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const res = await fetch('/api/users/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: newUsername,
                    email: newEmail || newUsername, // Fallback to username if email invalid/empty
                    password: newPassword,
                    role: newRole,
                    preferred_language: newLanguage,
                    group_id: 1 // V1 Default
                })
            })
            if (res.ok) {
                setShowCreateModal(false)
                setNewUsername('')
                setNewPassword('')
                setNewLanguage('de')
                fetchUsers()
            } else {
                alert('Erstellen fehlgeschlagen')
            }
        } catch (e) {
            console.error(e)
        }
    }

    const toggleUserStatus = async (user: User) => {
        if (!confirm(`User ${user.username} ${user.is_active ? 'deaktivieren' : 'aktivieren'}?`)) return
        try {
            await fetch(`/api/users/${user.id}`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ is_active: !user.is_active })
            })
            fetchUsers()
        } catch (e) {
            console.error(e)
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 p-8">
            <div className="max-w-6xl mx-auto space-y-6">

                {/* Header */}
                <div className="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800">Benutzerverwaltung</h1>
                        <p className="text-slate-500">Systemweite Benutzer & Rollen verwalten</p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        <span>Benutzer anlegen</span>
                    </button>
                </div>

                {/* User List */}
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 border-b border-slate-100">
                            <tr>
                                <th className="p-4 font-semibold text-slate-600">User</th>
                                <th className="p-4 font-semibold text-slate-600">Rolle(n)</th>
                                <th className="p-4 font-semibold text-slate-600">Sprache</th>
                                <th className="p-4 font-semibold text-slate-600">Status</th>
                                <th className="p-4 text-right font-semibold text-slate-600">Aktionen</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {users.map(u => (
                                <tr key={u.id} className="hover:bg-slate-50">
                                    <td className="p-4 font-medium text-slate-900 flex items-center space-x-3">
                                        <div className="bg-slate-100 p-2 rounded-full">
                                            <Users className="w-4 h-4 text-slate-500" />
                                        </div>
                                        <span>{u.username}</span>
                                        {u.is_superuser && <Shield className="w-3 h-3 text-indigo-500" />}
                                    </td>
                                    <td className="p-4">
                                        <div className="flex gap-1">
                                            {u.roles.map(r => (
                                                <span key={r} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded uppercase font-bold tracking-wide">
                                                    {r}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="p-4 text-sm text-slate-600">
                                        {u.preferred_language || 'de'}
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                            {u.is_active ? 'Aktiv' : 'Gesperrt'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <button
                                            onClick={() => toggleUserStatus(u)}
                                            className="text-sm font-medium text-slate-400 hover:text-slate-700 underline"
                                        >
                                            {u.is_active ? 'Sperren' : 'Aktivieren'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
                        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="text-xl font-bold">Neuen Benutzer anlegen</h3>
                            <button onClick={() => setShowCreateModal(false)}><X className="w-5 h-5 text-slate-400" /></button>
                        </div>
                        <form onSubmit={handleCreateUser} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">Username (Email recommended)</label>
                                <input
                                    type="text" required
                                    className="w-full p-2 border rounded"
                                    value={newUsername} onChange={e => setNewUsername(e.target.value)}
                                    placeholder="user@example.com"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">Email (Optional)</label>
                                <input
                                    type="email"
                                    className="w-full p-2 border rounded"
                                    placeholder="Same as username if empty"
                                    value={newEmail} onChange={e => setNewEmail(e.target.value)}
                                />
                                <p className="text-xs text-slate-500 mt-1">If using email as username, leave this blank or copy it.</p>
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">Passwort</label>
                                <input
                                    type="password" required
                                    className="w-full p-2 border rounded"
                                    value={newPassword} onChange={e => setNewPassword(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">Rolle</label>
                                <select
                                    className="w-full p-2 border rounded bg-white"
                                    value={newRole} onChange={e => setNewRole(e.target.value)}
                                >
                                    <option value="user">User (Standard)</option>
                                    <option value="viewer">Viewer (Read-Only)</option>
                                    <option value="superuser">Group Admin</option>
                                    <option value="admin">Platform Admin</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">Bevorzugte Sprache</label>
                                <select
                                    className="w-full p-2 border rounded bg-white"
                                    value={newLanguage} onChange={e => setNewLanguage(e.target.value)}
                                >
                                    <option value="de">Deutsch (German)</option>
                                    <option value="en">English</option>
                                    <option value="fr">Français (French)</option>
                                    <option value="es">Español (Spanish)</option>
                                    <option value="it">Italiano (Italian)</option>
                                    <option value="pt">Português (Portuguese)</option>
                                    <option value="nl">Nederlands (Dutch)</option>
                                    <option value="pl">Polski (Polish)</option>
                                    <option value="ru">Русский (Russian)</option>
                                    <option value="tr">Türkçe (Turkish)</option>
                                    <option value="da">Dansk (Danish)</option>
                                    <option value="sv">Svenska (Swedish)</option>
                                    <option value="no">Norsk (Norwegian)</option>
                                    <option value="fi">Suomi (Finnish)</option>
                                    <option value="el">Ελληνικά (Greek)</option>
                                    <option value="cs">Čeština (Czech)</option>
                                    <option value="hu">Magyar (Hungarian)</option>
                                    <option value="ro">Română (Romanian)</option>
                                    <option value="bg">Български (Bulgarian)</option>
                                    <option value="hr">Hrvatski (Croatian)</option>
                                    <option value="sk">Slovenčina (Slovak)</option>
                                    <option value="sl">Slovenščina (Slovenian)</option>
                                    <option value="et">Eesti (Estonian)</option>
                                    <option value="lv">Latviešu (Latvian)</option>
                                    <option value="lt">Lietuvių (Lithuanian)</option>
                                </select>
                            </div>
                            <button type="submit" className="w-full py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">
                                Benutzer erstellen
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
