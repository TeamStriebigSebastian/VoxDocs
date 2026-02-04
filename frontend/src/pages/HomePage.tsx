import { useNavigate } from 'react-router-dom'
import { Folder, Key, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function HomePage() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4 flex items-center justify-center">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">
            {t('home.title')}
          </h1>
          <p className="text-xl text-slate-600 mb-8">
            {t('home.subtitle')}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-800 mb-4">
              {t('home.welcome')}
            </h2>
            <p className="text-slate-600 mb-6">
              {t('home.environmentInfo')}
            </p>

            <div className="bg-slate-50 rounded-lg p-4 mb-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-2">
                <Key className="w-5 h-5 text-slate-400" />
                <span className="font-medium text-slate-700">{t('home.tenant')}</span>
                <span className="text-slate-900">Default Tenant (Self-Hosted)</span>
              </div>
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-slate-400" />
                <span className="font-medium text-slate-700">{t('home.configuration')}</span>
                <span className="text-slate-900">{t('home.configValue')}</span>
              </div>
            </div>

            <p className="text-sm text-slate-500 mb-8">
              {t('home.description')}
            </p>
          </div>

          <button
            onClick={() => navigate('/platform/cases')}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition-transform transform active:scale-95 flex items-center justify-center gap-3"
          >
            <Folder className="w-6 h-6" />
            <span>{t('home.openCaseManagement')}</span>
          </button>
        </div>

        <div className="mt-12 text-center text-slate-400 text-sm">
          <p>{t('home.version')}</p>
        </div>
      </div>
    </div>
  )
}
