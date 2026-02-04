import { useState, useEffect } from 'react'
import { Plus, Users, Shield, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from 'react-i18next'

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
    const { t } = useTranslation()
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
                alert(t('admin.createError'))
            }
        } catch (e) {
            console.error(e)
        }
    }

    const toggleUserStatus = async (user: User) => {
        if (!confirm(t('admin.confirmStatusChange', {
            username: user.username,
            action: user.is_active ? t('admin.ban') : t('admin.activate')
        }))) return

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
                        <h1 className="text-2xl font-bold text-slate-800">{t('admin.title')}</h1>
                        <p className="text-slate-500">{t('admin.subtitle')}</p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        <span>{t('admin.createUser')}</span>
                    </button>
                </div>

                {/* User List */}
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 border-b border-slate-100">
                            <tr>
                                <th className="p-4 font-semibold text-slate-600">{t('admin.user')}</th>
                                <th className="p-4 font-semibold text-slate-600">{t('admin.roles')}</th>
                                <th className="p-4 font-semibold text-slate-600">{t('admin.language')}</th>
                                <th className="p-4 font-semibold text-slate-600">{t('common.status')}</th>
                                <th className="p-4 text-right font-semibold text-slate-600">{t('common.actions')}</th>
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
                                            {u.is_active ? t('admin.active') : t('admin.banned')}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <button
                                            onClick={() => toggleUserStatus(u)}
                                            className="text-sm font-medium text-slate-400 hover:text-slate-700 underline"
                                        >
                                            {u.is_active ? t('admin.ban') : t('admin.activate')}
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
                            <h3 className="text-xl font-bold">{t('admin.createModalTitle')}</h3>
                            <button onClick={() => setShowCreateModal(false)}><X className="w-5 h-5 text-slate-400" /></button>
                        </div>
                        <form onSubmit={handleCreateUser} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">{t('admin.usernameLabel')}</label>
                                <input
                                    type="text" required
                                    className="w-full p-2 border rounded"
                                    value={newUsername} onChange={e => setNewUsername(e.target.value)}
                                    placeholder={t('admin.usernamePlaceholder')}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">{t('admin.emailLabel')}</label>
                                <input
                                    type="email"
                                    className="w-full p-2 border rounded"
                                    placeholder={t('admin.emailPlaceholder')}
                                    value={newEmail} onChange={e => setNewEmail(e.target.value)}
                                />
                                <p className="text-xs text-slate-500 mt-1">{t('admin.emailHint')}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">{t('admin.passwordLabel')}</label>
                                <input
                                    type="password" required
                                    className="w-full p-2 border rounded"
                                    value={newPassword} onChange={e => setNewPassword(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">{t('admin.roleLabel')}</label>
                                <select
                                    className="w-full p-2 border rounded bg-white"
                                    value={newRole} onChange={e => setNewRole(e.target.value)}
                                >
                                    <option value="user">User</option>
                                    <option value="viewer">Viewer</option>
                                    <option value="superuser">Group Admin</option>
                                    <option value="admin">Platform Admin</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-1">{t('admin.languageLabel')}</label>
                                <select
                                    className="w-full p-2 border rounded bg-white"
                                    value={newLanguage} onChange={e => setNewLanguage(e.target.value)}
                                >
                                    <option value="de">Deutsch (German)</option>
                                    <option value="en">English</option>
                                    <option value="fr">Français (French)</option>
                                    <option value="es">Español (Spanish)</option>
                                    {/* ... other options can be dynamic but ok for now */}
                                </select>
                            </div>
                            <button type="submit" className="w-full py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">
                                {t('admin.createAction')}
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
