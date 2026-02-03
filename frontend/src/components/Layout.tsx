import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import InstallButton from './InstallButton'
import SyncStatus from './SyncStatus'
import { Menu, X, Shield } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user } = useAuth()
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const isNursing = location.pathname.startsWith('/nursing') || location.pathname.startsWith('/appointment')
  const isPlatform = location.pathname.startsWith('/platform')
  const isCaseDetail = /^\/platform\/cases\/[^/]+$/.test(location.pathname)

  const dentalNavItems = [
    { path: '/', label: 'Aufnahme', icon: MicIcon },
    { path: '/recordings', label: 'Aufnahmen', icon: ListIcon },
    { path: '/onboarding', label: 'Training', icon: BookIcon },
  ]

  const nursingNavItems = [
    { path: '/nursing/appointment', label: 'Aufnahme', icon: MicIcon },
    { path: '/appointments', label: 'Termine', icon: CalendarIcon },
    { path: '/onboarding', label: 'Training', icon: BookIcon },
  ]

  const platformNavItems = [
    { path: '/platform/cases', label: 'Akten', icon: FolderIcon },
    // { path: '/platform/tasks', label: 'Aufgaben', icon: ListIcon }, // TODO
  ]

  let navItems = dentalNavItems
  // let headerTitle = 'VoxDocs Platform' // Replaced by Menu

  if (isNursing) {
    navItems = nursingNavItems
    // headerTitle = 'VoxDocs Platform'
  } else if (isPlatform) {
    navItems = platformNavItems
    // headerTitle = 'Platform Core'
  }


  return (
    <div className="min-h-screen flex flex-col bg-slate-50 safe-area-top safe-area-bottom">
      {/* PWA Install Banner */}
      <InstallButton />
      {/* Sync Status Banner */}
      <SyncStatus />

      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30">
        <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
          <Link to="/" className="text-xl font-bold text-primary-700 hover:text-primary-800 transition-colors">VoxDocs</Link>

          {/* Burger Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu Dropdown */}
        {isMenuOpen && (
          <div className="absolute top-full left-0 right-0 bg-white border-b border-slate-200 shadow-lg px-4 py-2 z-40 animate-in slide-in-from-top-2">
            <div className="max-w-7xl mx-auto flex flex-col space-y-2 pb-4">
              <Link
                to="/settings"
                className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-50 text-slate-700"
                onClick={() => setIsMenuOpen(false)}
              >
                <SettingsIcon className="w-5 h-5" />
                <span className="font-medium">Einstellungen</span>
              </Link>

              {user?.roles.some(r => r.role === 'admin') && (
                <Link
                  to="/platform/admin"
                  className="flex items-center space-x-3 p-3 rounded-lg hover:bg-slate-50 text-slate-700"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <Shield className="w-5 h-5" />
                  <span className="font-medium">Admin & User</span>
                </Link>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Main content - add padding-bottom for fixed nav ONLY if nav is visible */}
      <main className={`flex-1 px-4 py-6 max-w-7xl mx-auto w-full ${!isCaseDetail ? 'pb-24' : ''}`}>
        {children}
      </main>

      {/* Bottom navigation - Hidden on Case Detail Page (User Requirement: Button belongs in footer) */}
      {!isCaseDetail && (
        <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 px-4 py-2 z-50 safe-area-bottom">
          <div className="flex justify-around max-w-lg mx-auto">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex flex-col items-center py-2 px-4 rounded-lg transition-colors ${isActive
                    ? 'text-primary-600 bg-primary-50'
                    : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                  <Icon className="w-6 h-6" />
                  <span className="text-xs mt-1">{item.label}</span>
                </Link>
              )
            })}
          </div>
        </nav>
      )}
    </div>
  )
}

// Icon components
function MicIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  )
}

function ListIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  )
}

function BookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  )
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  )
}

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  )
}
