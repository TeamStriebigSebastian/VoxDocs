import { useNavigate } from 'react-router-dom'
import { Folder, Key, Settings } from 'lucide-react'

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4 flex items-center justify-center">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight">
            VoxDocs Platform
          </h1>
          <p className="text-xl text-slate-600 mb-8">
            Generic Documentation Engine Core
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-800 mb-4">
              Welcome
            </h2>
            <p className="text-slate-600 mb-6">
              You are running the generic platform core. This environment is configured for:
            </p>

            <div className="bg-slate-50 rounded-lg p-4 mb-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-2">
                <Key className="w-5 h-5 text-slate-400" />
                <span className="font-medium text-slate-700">Tenant:</span>
                <span className="text-slate-900">Default Tenant (Self-Hosted)</span>
              </div>
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-slate-400" />
                <span className="font-medium text-slate-700">Configuration:</span>
                <span className="text-slate-900">Generic Case Management</span>
              </div>
            </div>

            <p className="text-sm text-slate-500 mb-8">
              Manage generic case files, configurable entries, and tasks without domain-specific constraints.
            </p>
          </div>

          <button
            onClick={() => navigate('/platform/cases')}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-6 rounded-xl shadow-lg transition-transform transform active:scale-95 flex items-center justify-center gap-3"
          >
            <Folder className="w-6 h-6" />
            <span>Open Case Management</span>
          </button>
        </div>

        <div className="mt-12 text-center text-slate-400 text-sm">
          <p>VoxDocs Generic Core • v0.1.0-platform</p>
        </div>
      </div>
    </div>
  )
}
