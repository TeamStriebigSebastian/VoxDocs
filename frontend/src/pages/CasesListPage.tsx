import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen, Clock, Download } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from 'react-i18next'

interface CaseFile {
    id: number
    uuid: string
    title: string
    status: string
    updated_at: string
}

export default function CasesListPage() {
    const navigate = useNavigate()
    const { t } = useTranslation()
    const [cases, setCases] = useState<CaseFile[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [newCaseTitle, setNewCaseTitle] = useState('')
    const [exportingCase, setExportingCase] = useState<string | null>(null)

    const { accessToken, logout } = useAuth()

    useEffect(() => {
        if (accessToken) fetchCases()
    }, [accessToken])

    const fetchCases = async () => {
        try {
            // Hardcoded group_id=1 for now (Generic Default Group)
            const response = await fetch('/api/cases/?group_id=1', {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            })
            if (response.ok) {
                const data = await response.json()
                setCases(data)
            } else if (response.status === 401) {
                logout()
            }
        } catch (error) {
            console.error('Error fetching cases:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleCreateCase = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const response = await fetch('/api/cases/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify({
                    group_id: 1,
                    title: newCaseTitle
                })
            })

            if (response.ok) {
                setShowCreateModal(false)
                setNewCaseTitle('')
                fetchCases() // Refresh list
            }
        } catch (error) {
            console.error('Error creating case:', error)
            alert(t('cases.createError'))
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 p-8">
            <div className="max-w-6xl mx-auto space-y-6">

                {/* Header */}
                <div className="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800">{t('cases.title')}</h1>
                        <p className="text-slate-500">{t('cases.subtitle')}</p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        <span>{t('cases.newCase')}</span>
                    </button>
                </div>

                {/* List */}
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                    {isLoading ? (
                        <div className="p-8 text-center text-slate-500">{t('cases.loading')}</div>
                    ) : cases.length === 0 ? (
                        <div className="p-12 text-center text-slate-500">
                            <FolderOpen className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                            <p>{t('cases.empty')}</p>
                        </div>
                    ) : (
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 border-b border-slate-100">
                                <tr>
                                    <th className="p-4 font-semibold text-slate-600">{t('common.title')}</th>
                                    <th className="p-4 font-semibold text-slate-600">{t('common.status')}</th>
                                    <th className="p-4 font-semibold text-slate-600">{t('common.updated')}</th>
                                    <th className="p-4 font-semibold text-slate-600 text-right">{t('common.actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {cases.map((c) => (
                                    <tr
                                        key={c.id}
                                        className="hover:bg-slate-50 cursor-pointer transition-colors"
                                        onClick={() => navigate(`/platform/cases/${c.uuid}`)}
                                    >
                                        <td className="p-4 font-medium text-slate-900 flex items-center space-x-3">
                                            <div className="bg-blue-100 p-2 rounded-lg text-blue-600">
                                                <FolderOpen className="w-5 h-5" />
                                            </div>
                                            <span>{c.title}</span>
                                        </td>
                                        <td className="p-4">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                                                }`}>
                                                {t(`common.${c.status}`, { defaultValue: c.status.toUpperCase() })}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-500 text-sm flex items-center space-x-2">
                                            <Clock className="w-4 h-4" />
                                            <span>{c.updated_at ? new Date(c.updated_at).toLocaleString('de-DE') : '-'}</span>
                                        </td>
                                        <td className="p-4 text-right">
                                            <div className="flex items-center justify-end space-x-2">
                                                <button
                                                    onClick={async (e) => {
                                                        e.stopPropagation()
                                                        setExportingCase(c.uuid)
                                                        try {
                                                            const response = await fetch(`/api/exports/case/${c.uuid}`, {
                                                                headers: { 'Authorization': `Bearer ${accessToken}` }
                                                            })
                                                            if (response.ok) {
                                                                const blob = await response.blob()
                                                                const url = URL.createObjectURL(blob)
                                                                const a = document.createElement('a')
                                                                a.href = url
                                                                const disposition = response.headers.get('Content-Disposition')
                                                                const filenameMatch = disposition?.match(/filename="(.+)"/)
                                                                a.download = filenameMatch ? filenameMatch[1] : `${c.title}.zip`
                                                                document.body.appendChild(a)
                                                                a.click()
                                                                document.body.removeChild(a)
                                                                URL.revokeObjectURL(url)
                                                            } else {
                                                                console.error('Export failed:', response.status)
                                                            }
                                                        } catch (err) {
                                                            console.error('Export error:', err)
                                                        } finally {
                                                            setExportingCase(null)
                                                        }
                                                    }}
                                                    disabled={exportingCase === c.uuid}
                                                    className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                                                    title={t('cases.export')}
                                                >
                                                    <Download className={`w-4 h-4 ${exportingCase === c.uuid ? 'animate-pulse' : ''}`} />
                                                </button>
                                                <span className="text-blue-600 font-medium">
                                                    {t('common.open')}
                                                </span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* Case Creation Wizard Usage */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden transform transition-all scale-100">

                        {/* Modal Header */}
                        <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800">{t('cases.createTitle')}</h3>
                                <p className="text-sm text-slate-500 mt-1">{t('cases.createSubtitle')}</p>
                            </div>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors"
                            >
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Modal Body */}
                        <form onSubmit={handleCreateCase} className="p-6 space-y-6">

                            {/* Title Input */}
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-2">
                                    {t('cases.caseTitleLabel')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    autoFocus
                                    placeholder={t('cases.caseTitlePlaceholder')}
                                    className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                                    value={newCaseTitle}
                                    onChange={(e) => setNewCaseTitle(e.target.value)}
                                />
                                <p className="text-xs text-slate-500 mt-2">
                                    {t('cases.caseTitleHint')}
                                </p>
                            </div>

                            {/* Info Box */}
                            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 flex items-start space-x-3">
                                <FolderOpen className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                <div className="text-sm text-blue-800">
                                    <p className="font-medium">{t('cases.autoAssign')}</p>
                                    <p
                                        className="mt-1 text-blue-600/90"
                                        dangerouslySetInnerHTML={{ __html: t('cases.autoAssignText') }}
                                    />
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex justify-end space-x-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-5 py-2.5 text-slate-600 font-medium hover:bg-slate-50 rounded-lg transition-colors"
                                >
                                    {t('common.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={!newCaseTitle.trim()}
                                    className="px-5 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all focus:ring-4 focus:ring-blue-100"
                                >
                                    {t('cases.createAction')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

        </div>
    )
}
