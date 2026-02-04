import { useState, useEffect } from 'react'
import { Plus, FolderTree, Trash2, Edit2, User as UserIcon, Building, Users, Globe } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from 'react-i18next'

// Interfaces
interface Category {
  id: number
  name: string
  guidelines: string
  keywords: string | null
}

interface Group {
  id: number
  name: string
  tenant_id: number
}

interface User {
  id: number
  username: string
  is_superuser: boolean
}

export default function SettingsPage() {
  const { t, i18n } = useTranslation()

  // State
  const [categories, setCategories] = useState<Category[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [currentUser, setCurrentUser] = useState<User | null>(null)

  // Auth Context
  const { accessToken } = useAuth()

  // UI State
  const [loading, setLoading] = useState(true)
  const [selectedGroupId, setSelectedGroupId] = useState<number>(1) // Default to 1

  // Edit/Create State
  const [isCreating, setIsCreating] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [formName, setFormName] = useState('')
  const [formGuidelines, setFormGuidelines] = useState('')
  const [formKeywords, setFormKeywords] = useState('')

  // Server Settings
  const [serverSettings, setServerSettings] = useState<{ default_language: string, tenant_name: string } | null>(null)

  // Hardcoded Tenant Context (V1)
  const tenantName = "Default Tenant (Self-Hosted)"

  useEffect(() => {
    if (accessToken) {
      loadInitialData()
    }
  }, [accessToken])

  useEffect(() => {
    if (selectedGroupId && accessToken) {
      loadCategories(selectedGroupId)
    }
  }, [selectedGroupId, accessToken])

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  }

  const loadInitialData = async () => {
    if (!accessToken) return

    try {
      setLoading(true)
      const [userRes, groupsRes, settingsRes] = await Promise.all([
        fetch('/api/users/me', { headers: { 'Authorization': `Bearer ${accessToken}` } }),
        fetch('/api/groups/', { headers: { 'Authorization': `Bearer ${accessToken}` } }),
        fetch('/api/settings/', { headers: { 'Authorization': `Bearer ${accessToken}` } })
      ])

      if (userRes.ok) setCurrentUser(await userRes.json())
      if (groupsRes.ok) {
        const groupsData = await groupsRes.json()
        setGroups(groupsData)
        if (groupsData.length > 0) {
          setSelectedGroupId(groupsData[0].id)
        }
      }
      if (settingsRes.ok) {
        setServerSettings(await settingsRes.json())
      }
    } catch (e) {
      console.error("Failed to load settings data", e)
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async (groupId: number) => {
    if (!accessToken) return

    try {
      const res = await fetch(`/api/categories/?group_id=${groupId}`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      })
      if (res.ok) {
        setCategories(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleSaveCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formName.trim() || !accessToken) return

    try {
      let res
      if (editingCategory) {
        // UPDATE
        res = await fetch(`/api/categories/${editingCategory.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            name: formName,
            guidelines: formGuidelines,
            keywords: formKeywords
          })
        })
      } else {
        // CREATE
        res = await fetch('/api/categories/', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            group_id: selectedGroupId,
            name: formName,
            guidelines: formGuidelines,
            keywords: formKeywords
          })
        })
      }

      if (res.ok) {
        resetForm()
        loadCategories(selectedGroupId)
      } else {
        const err = await res.json()
        alert(`${t('common.error')}: ${err.detail || 'Speichern fehlgeschlagen'}`)
      }
    } catch (e) {
      console.error(e)
      alert("Netzwerkfehler beim Speichern.")
    }
  }

  const handleSaveSettings = async (lang: string) => {
    if (!accessToken) return
    try {
      const res = await fetch('/api/settings/', {
        method: 'PUT',
        headers,
        body: JSON.stringify({ default_language: lang })
      })
      if (res.ok) {
        setServerSettings(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleDeleteCategory = async (id: number) => {
    if (!accessToken) return
    if (!confirm(t('common.confirmDelete'))) return

    try {
      const res = await fetch(`/api/categories/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      })
      if (res.ok) {
        loadCategories(selectedGroupId)
      } else {
        alert("Löschen fehlgeschlagen.")
      }
    } catch (e) {
      console.error(e)
    }
  }

  const startEdit = (cat: Category) => {
    setEditingCategory(cat)
    setFormName(cat.name)
    setFormGuidelines(cat.guidelines || '')
    setFormKeywords(cat.keywords || '')
    setIsCreating(true)
  }

  const resetForm = () => {
    setIsCreating(false)
    setEditingCategory(null)
    setFormName('')
    setFormGuidelines('')
    setFormKeywords('')
  }

  if (loading) return <div className="p-12 text-center text-slate-500">{t('common.loading')}</div>

  return (
    <div className="max-w-5xl mx-auto space-y-8 p-6">

      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">{t('settings.title')}</h1>
        <p className="text-slate-500 mt-2">{t('settings.subtitle')}</p>
      </header>

      {/* 1. Context & User Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* User Card */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 col-span-1">
          <div className="flex items-center space-x-3 mb-4">
            <div className="bg-emerald-100 p-2 rounded-lg">
              <UserIcon className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">{t('settings.profile.title')}</h2>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 uppercase font-semibold">{t('settings.profile.username')}</label>
              <div className="text-slate-900 font-medium">{currentUser?.username || 'Unknown'}</div>
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase font-semibold">{t('settings.profile.role')}</label>
              <div className="inline-flex items-center px-2 py-1 bg-slate-100 rounded text-xs font-medium text-slate-600 mt-1">
                {currentUser?.is_superuser ? t('settings.profile.admin') : t('settings.profile.user')}
              </div>
            </div>
          </div>
        </div>

        {/* Tenant & Group Context */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 col-span-1 md:col-span-2">
          <div className="flex items-center space-x-3 mb-4">
            <div className="bg-indigo-100 p-2 rounded-lg">
              <Building className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-800">{t('settings.workspace.title')}</h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">{t('settings.workspace.tenant')}</label>
              <div className="p-3 bg-slate-50 rounded border border-slate-200 text-slate-700 font-medium flex items-center">
                <Building className="w-4 h-4 mr-2 text-slate-400" />
                {tenantName}
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">{t('settings.workspace.activeGroup')}</label>
              <div className="relative">
                <Users className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                <select
                  className="w-full pl-10 pr-4 py-3 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-medium text-slate-700 appearance-none"
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(Number(e.target.value))}
                >
                  {groups.map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-slate-500 mt-1">{t('settings.workspace.switchGroupHint')}</p>
            </div>

            {/* UI Language Setting */}
            <div className="col-span-1 border-t border-slate-100 pt-4 mt-2">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">{t('settings.uiLanguage.label')}</label>
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <Globe className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                  <select
                    className="pl-10 pr-8 bg-white border border-slate-300 rounded-lg py-2 text-sm font-medium text-slate-700 appearance-none"
                    value={i18n.language}
                    onChange={(e) => i18n.changeLanguage(e.target.value)}
                  >
                    <option value="de">Deutsch</option>
                    <option value="en">English</option>
                  </select>
                </div>
                <span className="text-xs text-slate-400">
                  {t('settings.uiLanguage.hint')}
                </span>
              </div>
            </div>

            {/* Default Language Setting */}
            {currentUser?.is_superuser && (
              <div className="col-span-1 md:col-span-2 pt-4 border-t border-slate-100 mt-2">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">{t('settings.server.defaultLanguage')}</label>
                <div className="flex items-center space-x-4">
                  <select
                    className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium text-slate-700"
                    value={serverSettings?.default_language || 'de'}
                    onChange={(e) => handleSaveSettings(e.target.value)}
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
                  <span className="text-xs text-slate-400">
                    {t('settings.server.hint')}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Group Configuration (Categories) */}
      <div className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-xl font-bold text-slate-800">{t('settings.categories.title')}</h2>
            <p className="text-sm text-slate-500">{t('settings.categories.subtitle')} <strong>{groups.find(g => g.id === selectedGroupId)?.name}</strong></p>
          </div>
          {!isCreating && (
            <button
              className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors shadow-sm"
              onClick={() => {
                setEditingCategory(null)
                setFormName('')
                setFormGuidelines('')
                setIsCreating(true)
              }}
            >
              <Plus className="w-4 h-4" />
              <span>{t('settings.categories.newCategory')}</span>
            </button>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {/* Form */}
          {isCreating && (
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6 animate-in fade-in slide-in-from-top-4">
              <h3 className="font-semibold text-slate-700 mb-4">{editingCategory ? t('settings.categories.editCategory') : t('settings.categories.newCategory')}</h3>
              <form onSubmit={handleSaveCategory} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">{t('settings.categories.form.name')}</label>
                  <input
                    type="text"
                    value={formName}
                    onChange={e => setFormName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 font-medium"
                    placeholder={t('settings.categories.form.namePlaceholder')}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {t('settings.categories.form.keywords')}
                  </label>
                  <input
                    type="text"
                    value={formKeywords}
                    onChange={e => setFormKeywords(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    placeholder={t('settings.categories.form.keywordsPlaceholder')}
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    {t('settings.categories.form.keywordsHint')}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">{t('settings.categories.form.guidelines')}</label>
                  <textarea
                    value={formGuidelines}
                    onChange={e => setFormGuidelines(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 text-sm"
                    rows={3}
                    placeholder={t('settings.categories.form.guidelinesPlaceholder')}
                  />
                </div>
                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={resetForm}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded text-sm transition-colors"
                  >
                    {t('common.cancel')}
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium shadow-sm transition-colors"
                  >
                    {t('common.save')}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Category List */}
          <div className="space-y-3">
            {categories.length === 0 && !isCreating && (
              <div className="text-center py-12 text-slate-400 bg-slate-50 rounded border border-dashed border-slate-200">
                <FolderTree className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p>{t('settings.categories.noCategories')}</p>
              </div>
            )}
            {categories.map((cat) => (
              <div key={cat.id} className="bg-white border border-slate-200 rounded-lg p-4 flex justify-between items-start group hover:border-slate-300 transition-colors shadow-sm">
                <div>
                  <div className="flex items-center space-x-2">
                    <h4 className="font-bold text-slate-800">{cat.name}</h4>
                  </div>
                  {cat.keywords && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {cat.keywords.split(',').map((k, i) => (
                        <span key={i} className="inline-block bg-slate-100 text-slate-600 text-[10px] px-1.5 py-0.5 rounded border border-slate-200">
                          {k.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                  {cat.guidelines && (
                    <p className="text-sm text-slate-500 mt-2 line-clamp-2">{cat.guidelines}</p>
                  )}
                </div>
                <div className="flex space-x-1 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => startEdit(cat)}
                    className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteCategory(cat.id)}
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div >
  )
}
